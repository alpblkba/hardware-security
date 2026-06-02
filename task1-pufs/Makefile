TOPLEVEL = top_level
VERILOG_FILES = $(TOPLEVEL).v uart.v puf_module.v combined_ram.v
PCF = LatticeiCE40HX8K.pcf
DEVICE = hx8k
PACKAGE = ct256
YOSYS=yosys
NEXTPNR=nextpnr-ice40
MHZ=12

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

%.asc: %.json $(PCF)
	$(NEXTPNR) -q \
	--$(DEVICE) --package $(PACKAGE) \
	--freq $(MHZ) \
	-l "${TOPLEVEL}_nextpnr.log" \
	--json $< --pcf $(PCF) --pcf-allow-unconstrained --asc $@

%.bin: %.asc
	# task 1 PUF: do not initialize BRAM to zero; keep SRAM/BRAM power-up state observable
	icepack -n $< $@

%.rpt: %.asc
	icetime -d $(DEVICE) -mtr $@ $<

prog: $(TOPLEVEL).bin $(TOPLEVEL).rpt
	iceprog -S $<

prog-flash: $(TOPLEVEL).bin $(TOPLEVEL).rpt
	iceprog $<

clean:
	-rm -f $(TOPLEVEL).blif $(TOPLEVEL).asc $(TOPLEVEL).rpt $(TOPLEVEL).bin $(TOPLEVEL).json $(TOPLEVEL)_yosys.log $(TOPLEVEL)_nextpnr.log

.SECONDARY:
.PHONY: all prog clean

# -----------------------------------------------------------------------------
# Alp-readable local workflow targets
# These targets do not replace the assignment-provided rules.
# They wrap the exact manual bring-up/debug commands in readable make targets.
# -----------------------------------------------------------------------------

TOP        ?= top_level
RTL        := rtl/top_level.v rtl/uart.v rtl/puf_module.v rtl/combined_ram.v
PCF        := constraints/LatticeiCE40HX8K.pcf
DEVICE     := hx8k
PACKAGE    := ct256
FREQ       := 12
PORT       ?= /dev/cu.usbserial-21201
REQUEST    ?= s
OUT        ?= puf_data.txt

.PHONY: alp-clean alp-build alp-program alp-capture alp-debug alp-run alp-check

alp-clean:
	rm -f $(TOP).json $(TOP).asc $(TOP).bin $(TOP)_noinit.bin $(TOP).rpt
	rm -f $(TOP)_yosys.log $(TOP)_nextpnr.log

alp-build: alp-clean
	@echo "[alp-build] yosys: synthesize RTL into $(TOP).json"
	yosys -q \
	  -L $(TOP)_yosys.log \
	  -p "hierarchy -top $(TOP)" \
	  -p "synth_ice40 -json $(TOP).json" \
	  $(RTL)

	@echo "[alp-build] nextpnr: place-and-route into $(TOP).asc"
	nextpnr-ice40 -q \
	  --$(DEVICE) --package $(PACKAGE) \
	  --freq $(FREQ) \
	  -l $(TOP)_nextpnr.log \
	  --json $(TOP).json \
	  --pcf $(PCF) \
	  --pcf-allow-unconstrained \
	  --asc $(TOP).asc

	@echo "[alp-build] icetime: timing report into $(TOP).rpt"
	icetime -d $(DEVICE) -mtr $(TOP).rpt $(TOP).asc

	@echo "[alp-build] icepack -n: pack bitstream without BRAM initialization"
	icepack -n $(TOP).asc $(TOP)_noinit.bin

	@echo "[alp-build] done: $(TOP)_noinit.bin"

alp-program:
	@echo "[alp-program] programming SRAM with $(TOP)_noinit.bin"
	iceprog -S $(TOP)_noinit.bin

alp-capture:
	@echo "[alp-capture] request=$(REQUEST) port=$(PORT) out=$(OUT)"
	./scripts/get_puf_from_device.py \
	  --no-reset \
	  -p $(PORT) \
	  --request-byte $(REQUEST) \
	  -o $(OUT)

alp-debug:
	$(MAKE) alp-capture REQUEST=d OUT=debug_packet_16k.txt

alp-run: alp-build alp-program alp-capture

alp-check:
	python3 -c 'from pathlib import Path; import re; src = Path("$(OUT)"); text = src.read_text(); lines = text.strip().splitlines(); s = "".join(lines); print("file:", src); print("lines:", len(lines)); print("hex chars:", len(s)); print("unique chars:", sorted(set(s))); print("nonzero hex chars:", sum(c != "0" for c in s)); print("first line:", lines[0] if lines else ""); print("shape ok:", len(lines) == 512 and all(len(line) == 64 for line in lines)); m = Path("measurements"); m.mkdir(exist_ok=True); files = sorted(m.glob("puf_data_*.txt")); dup = next((p for p in files if p.read_text() == text), None); nums = [int(re.match(r"puf_data_(\d+)\.txt", p.name).group(1)) for p in files if re.match(r"puf_data_(\d+)\.txt", p.name)]; n = max(nums, default=-1) + 1; dst = m / f"puf_data_{n:02d}.txt"; print("warning: identical capture already exists:", dup, "-- not saving a new measurement") if dup else (dst.write_text(text), print("saved new measurement:", dst))'
