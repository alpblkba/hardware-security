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
	@grep -E "SB_LUT4|SB_RAM40_4K|Number of cells" "${TOPLEVEL}_yosys.log" || true
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
	icetime -d $(DEVICE) -m -t -r ${TOPLEVEL}_icetime.log $<
	@cp ${TOPLEVEL}_icetime.log $@

report-info: $(TOPLEVEL).rpt $(TOPLEVEL)_nextpnr.log $(TOPLEVEL)_yosys.log
	@grep -E "SB_LUT4|SB_RAM40_4K|Number of cells" ${TOPLEVEL}_yosys.log || true
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

# macOS/local verification helpers
# Simulation uses Homebrew Icarus Verilog because cocotb/Python embedding is more stable there.
# FPGA build/programming uses oss-cad-suite for yosys, nextpnr, icetime, icepack, and iceprog.

OSS_CAD_BIN ?= $(HOME)/Documents/tools/oss-cad-suite/bin
HOMEBREW_BIN ?= /opt/homebrew/bin
UART_PORT ?= /dev/cu.usbserial-21401
VENV ?= .venv-cocotb

.PHONY: sim-macos
sim-macos:
	@echo "running cocotb simulation with Homebrew Icarus Verilog"
	@echo "using ICARUS_BIN_DIR=$(HOMEBREW_BIN)"
	@PYGPI_PYTHON_BIN="$$(pwd)/$(VENV)/bin/python3" \
	LIBPYTHON_LOC="$$($(VENV)/bin/python3 - <<'PY'\nimport sysconfig\nprint(sysconfig.get_config_var('LIBDIR') + '/libpython' + sysconfig.get_config_var('LDVERSION') + '.dylib')\nPY\n)" \
	ICARUS_BIN_DIR=$(HOMEBREW_BIN) \
	$(MAKE) sim

.PHONY: build-macos
build-macos:
	@echo "running fpga build with oss-cad-suite"
	@PATH="$(OSS_CAD_BIN):/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
	$(MAKE) all
	@PATH="$(OSS_CAD_BIN):/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
	$(MAKE) report-info

.PHONY: prog-macos
prog-macos:
	@echo "programming fpga with oss-cad-suite"
	@PATH="$(OSS_CAD_BIN):/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
	$(MAKE) prog

.PHONY: board-test
board-test:
	@echo "running uart board test on $(UART_PORT)"
	@DEV_UART=$(UART_PORT) $(VENV)/bin/python3 check_aes.py

.PHONY: verify-macos
verify-macos: clean sim-macos build-macos prog-macos board-test
