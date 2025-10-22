* Auto-generated SPICE netlist from MCTS topology generator

* Power supply
VDD VDD 0 DC 5V

* Input signal
VIN n0 0 AC 1V

* Circuit components
M1 n1 n0 VDD VDD PMOS_MODEL L=1u W=10u
M2 n1 n0 0 0 NMOS_MODEL L=1u W=10u
R1 n1 0 1k

* Output probe
.print ac v(n1)

* Device models
.model DMOD D
.model NMOS_MODEL NMOS (LEVEL=1 VTO=0.7 KP=20u)
.model PMOS_MODEL PMOS (LEVEL=1 VTO=-0.7 KP=10u)
.model NPN_MODEL NPN (BF=100)
.model PNP_MODEL PNP (BF=100)

* Simulation commands
.ac dec 100 1 1MEG
.end