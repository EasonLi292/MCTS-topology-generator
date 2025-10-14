* Auto-generated SPICE netlist from MCTS topology generator

* Power supply
VDD VDD 0 DC 5V

* Input signal
VIN n4 0 AC 1V

* Circuit components
P1 0 0 0 PNP_MODEL

* Output probe
.print ac v(n4)

* Device models
.model DMOD D
.model NMOS_MODEL NMOS (LEVEL=1)
.model PMOS_MODEL PMOS (LEVEL=1)
.model NPN_MODEL NPN
.model PNP_MODEL PNP

* Simulation commands
.ac dec 100 1 1MEG
.end