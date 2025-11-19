#!/usr/bin/env python3
"""
Analyze and evaluate the quality of a generated circuit topology.
"""

import sys
import os
import subprocess
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from topology_game_board import Breadboard


def analyze_netlist(netlist):
    """Analyze the SPICE netlist structure."""
    print("="*70)
    print("NETLIST ANALYSIS")
    print("="*70)

    lines = netlist.strip().split('\n')

    # Count components
    components = {
        'Resistors': 0,
        'Capacitors': 0,
        'Inductors': 0,
        'NMOS': 0,
        'PMOS': 0,
        'NPN': 0,
        'PNP': 0,
        'Diodes': 0
    }

    nodes = set()
    component_details = []

    for line in lines:
        line = line.strip()
        if not line or line.startswith('*') or line.startswith('.'):
            continue

        if line.startswith('V'):
            continue  # Skip voltage sources

        parts = line.split()
        if len(parts) < 2:
            continue

        comp_name = parts[0]

        if comp_name.startswith('R'):
            components['Resistors'] += 1
            nodes.update(parts[1:3])
            component_details.append(f"  {comp_name}: {parts[1]} → {parts[2]} ({parts[3]})")
        elif comp_name.startswith('C'):
            components['Capacitors'] += 1
            nodes.update(parts[1:3])
            component_details.append(f"  {comp_name}: {parts[1]} ↔ {parts[2]} ({parts[3]})")
        elif comp_name.startswith('L'):
            components['Inductors'] += 1
            nodes.update(parts[1:3])
            component_details.append(f"  {comp_name}: {parts[1]} ↔ {parts[2]} ({parts[3]})")
        elif comp_name.startswith('M'):
            # MOSFET format: M<name> <drain> <gate> <source> <bulk> <model> ...
            model = parts[5] if len(parts) > 5 else ''
            if 'NMOS' in model.upper():
                components['NMOS'] += 1
                nodes.update([parts[1], parts[2], parts[3], parts[4]])
                component_details.append(f"  {comp_name}: D={parts[1]} G={parts[2]} S={parts[3]} B={parts[4]} (NMOS)")
            elif 'PMOS' in model.upper():
                components['PMOS'] += 1
                nodes.update([parts[1], parts[2], parts[3], parts[4]])
                component_details.append(f"  {comp_name}: D={parts[1]} G={parts[2]} S={parts[3]} B={parts[4]} (PMOS)")
        elif comp_name.startswith('Q'):
            model = parts[4] if len(parts) > 4 else ''
            if 'NPN' in model:
                components['NPN'] += 1
                nodes.update(parts[1:4])
                component_details.append(f"  {comp_name}: C={parts[1]} B={parts[2]} E={parts[3]} (NPN)")
            elif 'PNP' in model:
                components['PNP'] += 1
                nodes.update(parts[1:4])
                component_details.append(f"  {comp_name}: C={parts[1]} B={parts[2]} E={parts[3]} (PNP)")
        elif comp_name.startswith('D'):
            components['Diodes'] += 1
            nodes.update(parts[1:3])
            component_details.append(f"  {comp_name}: {parts[1]} → {parts[2]}")

    print("\nComponent Count:")
    total = 0
    for comp_type, count in components.items():
        if count > 0:
            print(f"  {comp_type}: {count}")
            total += count
    print(f"  TOTAL: {total}")

    print(f"\nUnique Nodes: {len(nodes)}")
    print(f"Nodes: {sorted(nodes, key=lambda x: (x != '0', x))}")

    print("\nComponent Details:")
    for detail in component_details:
        print(detail)

    return components, nodes


def evaluate_topology(components, nodes):
    """Evaluate the quality of the circuit topology."""
    print("\n" + "="*70)
    print("TOPOLOGY EVALUATION")
    print("="*70)

    score = 0
    issues = []
    strengths = []

    # 1. Component Diversity
    unique_types = sum(1 for count in components.values() if count > 0)
    if unique_types >= 3:
        strengths.append(f"Good component diversity ({unique_types} types)")
        score += 20
    elif unique_types >= 2:
        strengths.append(f"Moderate component diversity ({unique_types} types)")
        score += 10
    else:
        issues.append(f"Low component diversity ({unique_types} type)")

    # 2. Circuit Complexity
    total_components = sum(components.values())
    if total_components >= 5:
        strengths.append(f"Good complexity ({total_components} components)")
        score += 15
    elif total_components >= 3:
        strengths.append(f"Moderate complexity ({total_components} components)")
        score += 10
    else:
        issues.append(f"Low complexity ({total_components} components)")

    # 3. Active vs Passive
    active = components['NMOS'] + components['PMOS'] + components['NPN'] + components['PNP']
    passive = components['Resistors'] + components['Capacitors'] + components['Inductors']

    if active > 0 and passive > 0:
        strengths.append(f"Mixed active ({active}) and passive ({passive}) components")
        score += 20
    elif active > 0:
        issues.append("Only active components (no passive)")
        score -= 5
    elif passive > 0:
        issues.append("Only passive components (no active)")
        score -= 5

    # 4. Transistor Usage
    if components['NMOS'] > 0 and components['PMOS'] > 0:
        strengths.append("CMOS configuration possible")
        score += 15

    if components['NPN'] > 0 or components['PNP'] > 0:
        strengths.append("BJT amplification possible")
        score += 10

    # 5. Frequency response elements
    if components['Inductors'] > 0 and components['Capacitors'] > 0:
        strengths.append("LC network for frequency response")
        score += 15
    elif components['Capacitors'] > 0:
        strengths.append("Capacitive elements for filtering")
        score += 5
    elif components['Inductors'] > 0:
        strengths.append("Inductive elements present")
        score += 5

    # 6. Node connectivity
    if len(nodes) >= 3:
        strengths.append(f"Multiple internal nodes ({len(nodes)})")
        score += 10
    else:
        issues.append(f"Few internal nodes ({len(nodes)})")

    print("\nStrengths:")
    for s in strengths:
        print(f"  ✓ {s}")

    if issues:
        print("\nPotential Issues:")
        for i in issues:
            print(f"  ⚠ {i}")

    print(f"\nQuality Score: {score}/100")

    if score >= 80:
        grade = "Excellent"
    elif score >= 60:
        grade = "Good"
    elif score >= 40:
        grade = "Fair"
    else:
        grade = "Poor"

    print(f"Overall Grade: {grade}")

    return score, grade


def circuit_type_analysis(components):
    """Determine likely circuit type/function."""
    print("\n" + "="*70)
    print("CIRCUIT TYPE ANALYSIS")
    print("="*70)

    likely_functions = []

    # Amplifier characteristics
    if components['NPN'] > 0 or components['PNP'] > 0:
        likely_functions.append("BJT Amplifier (common emitter/collector configuration)")

    if components['NMOS'] > 0 or components['PMOS'] > 0:
        likely_functions.append("MOSFET Amplifier/Switch")

    if components['NMOS'] > 0 and components['PMOS'] > 0:
        likely_functions.append("CMOS Logic/Inverter")

    # Filter characteristics
    if components['Resistors'] > 0 and components['Capacitors'] > 0:
        likely_functions.append("RC Filter (low-pass/high-pass)")

    if components['Inductors'] > 0 and components['Capacitors'] > 0:
        likely_functions.append("LC Filter/Resonator")

    if components['Resistors'] > 0 and components['Inductors'] > 0 and components['Capacitors'] > 0:
        likely_functions.append("RLC Filter (band-pass/band-stop)")

    # Oscillator characteristics
    if components['Inductors'] > 0 and components['Capacitors'] > 0 and (components['NPN'] > 0 or components['NMOS'] > 0):
        likely_functions.append("Possible Oscillator (LC tank + active element)")

    print("\nLikely Circuit Functions:")
    if likely_functions:
        for func in likely_functions:
            print(f"  • {func}")
    else:
        print("  • Unidentified/Novel topology")

    return likely_functions


def analyze_circuit_from_netlist(netlist_text):
    """Complete analysis of circuit from netlist."""
    components, nodes = analyze_netlist(netlist_text)
    score, grade = evaluate_topology(components, nodes)
    functions = circuit_type_analysis(components)

    return {
        'components': components,
        'nodes': nodes,
        'score': score,
        'grade': grade,
        'functions': functions
    }


if __name__ == "__main__":
    import sys

    # Read the generated netlist (default to latest output)
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'outputs/mcts_from_scratch_8000iter.txt'

    with open(input_file, 'r') as f:
        content = f.read()

    # Extract netlist section
    netlist_start = content.find('Netlist:')
    if netlist_start == -1:
        print("No netlist found in output file")
        sys.exit(1)

    netlist = content[netlist_start + len('Netlist:'):].strip()

    print("="*70)
    print("CIRCUIT TOPOLOGY EVALUATION")
    print("From MCTS-generated circuit (8000 iterations)")
    print("="*70)
    print()

    result = analyze_circuit_from_netlist(netlist)

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total Components: {sum(result['components'].values())}")
    print(f"Component Types: {sum(1 for c in result['components'].values() if c > 0)}")
    print(f"Internal Nodes: {len(result['nodes'])}")
    print(f"Quality Score: {result['score']}/100")
    print(f"Grade: {result['grade']}")
    print(f"Likely Functions: {', '.join(result['functions']) if result['functions'] else 'Novel topology'}")
