TOPLEVEL = top_level
VERILOG_FILES = ${shell ls *.v}
PCF = LatticeiCE40HX8K.pcf
DEVICE = hx8k
PACKAGE = ct256
YOSYS=yosys
NEXTPNR=nextpnr-ice40
MHZ=12

LIBPYTHON_LOC = $(shell cocotb-config --libpython)
COCOTB_TEST_MODULES = testbench
COCOTB_TOPLEVEL = top_level
TOPLEVEL_LANG ?= verilog
SIM ?= icarus
SIM_BUILD = sim_build
COCOTB_RESULTS_FILE ?= results.xml
COCOTB_HDL_TIMEUNIT ?= 1ns
COCOTB_HDL_TIMEPRECISION ?= 1ps

CMD_BIN := iverilog

ifdef ICARUS_BIN_DIR
    CMD := $(shell :; command -v $(ICARUS_BIN_DIR)/$(CMD_BIN) 2>/dev/null)
else
    # auto-detect bin dir from system path
    CMD := $(shell :; command -v $(CMD_BIN) 2>/dev/null)
endif

ifeq (, $(CMD))
    $(error Unable to locate command >$(CMD_BIN)<)
else
    ICARUS_BIN_DIR := $(shell dirname $(CMD))
    export ICARUS_BIN_DIR
endif

COMPILE_ARGS += -f $(SIM_BUILD)/cmds.f

all: $(TOPLEVEL).rpt $(TOPLEVEL).bin

synth: $(TOPLEVEL).json

pnr: $(TOPLEVEL).asc

$(TOPLEVEL).json: $(VERILOG_FILES)
	$(YOSYS) -q \
	-L "${TOPLEVEL}_yosys.log" \
	-e 'Driver-driver conflict' \
	-p "hierarchy -top ${TOPLEVEL}" \
	-p "synth_ice40 ${YOSYS_OPTIONS} -json ${TOPLEVEL}.json" \
	$(VERILOG_FILES)
	@cat "${TOPLEVEL}_yosys.log" |grep "Number of cells:"
	@echo "FPGA (HX8K) maximum available number of cells: 7680"

%.asc: %.json $(PCF)
	$(NEXTPNR) -q \
	--$(DEVICE) --package $(PACKAGE) \
	--freq $(MHZ) \
	-l "${TOPLEVEL}_nextpnr.log" \
	--json $< --pcf $(PCF) --pcf-allow-unconstrained --asc $@
	@cat ${TOPLEVEL}_nextpnr.log  |grep "ICESTORM_LC:"

%.bin: %.asc
	icepack $< $@

%.rpt: %.asc
	icetime -d $(DEVICE) -mtr $@ $< -r ${TOPLEVEL}_icetime.log

report-info: $(TOPLEVEL).rpt $(TOPLEVEL)_nextpnr.log $(TOPLEVEL)_yosys.log
	@cat ${TOPLEVEL}_yosys.log |grep "Number of cells:"
	@cat ${TOPLEVEL}_nextpnr.log |grep "ICESTORM_LC:"
	@cat ${TOPLEVEL}_icetime.log |grep "Total path delay:"

prog: $(TOPLEVEL).bin $(TOPLEVEL).rpt
	iceprog -S $<

prog-flash: $(TOPLEVEL).bin $(TOPLEVEL).rpt
	iceprog $<

traces.fst: sim
sim: $(VERILOG_FILES) | $(SIM_BUILD)
	@echo $(CMD)
	@echo "+timescale+$(COCOTB_HDL_TIMEUNIT)/$(COCOTB_HDL_TIMEPRECISION)" > $(SIM_BUILD)/cmds.f
	$(CMD) -Wall -s top_level -o $(SIM_BUILD)/sim.vvp -g2012 $(COMPILE_ARGS) $(VERILOG_FILES)
	COCOTB_TEST_MODULES=$(COCOTB_TEST_MODULES) COCOTB_TOPLEVEL=$(COCOTB_TOPLEVEL) TOPLEVEL_LANG=$(TOPLEVEL_LANG) \
	$(ICARUS_BIN_DIR)/vvp -M $(shell cocotb-config --lib-dir) -m $(shell cocotb-config --lib-name vpi icarus) $(SIM_BUILD)/sim.vvp -fst

waveform: traces.fst
	gtkwave -a traces_gtkw.sav traces.fst

$(SIM_BUILD):
	mkdir -p $@

clean:
	-rm -f $(TOPLEVEL).blif $(TOPLEVEL).asc $(TOPLEVEL).rpt $(TOPLEVEL).bin $(TOPLEVEL).json $(TOPLEVEL)_yosys.log $(TOPLEVEL)_nextpnr.log
	-rm -f results.xml traces.fst
	-rm -R ./__pycache__
	-rm -R ./sim_build

.SECONDARY:
.PHONY: all prog clean
