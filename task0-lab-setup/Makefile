TOPLEVEL = top_level
VERILOG_FILES = $(TOPLEVEL).v uart.v
PCF = LatticeiCE40HX8K.pcf
DEVICE = hx8k
PACKAGE = ct256
YOSYS = yosys
NEXTPNR = nextpnr-ice40
MHZ = 12

all: $(TOPLEVEL).bin

$(TOPLEVEL).json: $(VERILOG_FILES)
	$(YOSYS) -q \
	-L "$(TOPLEVEL)_yosys.log" \
	-p "hierarchy -top $(TOPLEVEL)" \
	-p "synth_ice40 $(YOSYS_OPTIONS) -json $(TOPLEVEL).json" \
	$(VERILOG_FILES)

%.asc: %.json $(PCF)
	$(NEXTPNR) -q \
	--$(DEVICE) --package $(PACKAGE) \
	--freq $(MHZ) \
	-l "$(TOPLEVEL)_nextpnr.log" \
	--json $< --pcf $(PCF) --pcf-allow-unconstrained --asc $@

%.bin: %.asc
	icepack $< $@

timing: $(TOPLEVEL).asc
	-icetime -d $(DEVICE) -mtr $(TOPLEVEL).rpt $(TOPLEVEL).asc

prog: $(TOPLEVEL).bin
	iceprog -S $<

prog-flash: $(TOPLEVEL).bin
	iceprog $<

gui: $(TOPLEVEL).json $(PCF) $(TOPLEVEL).asc
	$(NEXTPNR) -q \
	--$(DEVICE) --package $(PACKAGE) \
	--json $(TOPLEVEL).json \
	--pcf $(PCF) \
	--asc $(TOPLEVEL).asc \
	--pcf-allow-unconstrained \
	--gui

clean:
	-rm -f $(TOPLEVEL).blif $(TOPLEVEL).asc $(TOPLEVEL).rpt $(TOPLEVEL).bin $(TOPLEVEL).json $(TOPLEVEL)_yosys.log $(TOPLEVEL)_nextpnr.log

.SECONDARY:
.PHONY: all prog prog-flash timing gui clean
