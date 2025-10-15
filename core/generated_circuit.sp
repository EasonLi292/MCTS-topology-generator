* Auto-generated SPICE netlist from MCTS topology generator

* Power supply
VDD VDD 0 DC 5V

* Input signal
VIN n0 0 AC 1V

* Circuit components
I1 n2 0 1m

* Output probe
.print ac v(n0)

* Device models
.model DMOD D
.model NMOS_MODEL NMOS (LEVEL=1)
.model PMOS_MODEL PMOS (LEVEL=1)
.model NPN_MODEL NPN
.model PNP_MODEL PNP

* Simulation commands
.ac dec 100 1 1MEG
.end