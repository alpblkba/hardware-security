import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, with_timeout
from cocotb.handle import Force, Release
from  cocotb.triggers import SimTimeoutError
import random
import aes
from aes.core import subbytes, shiftrows, mixcolumns, key_expansion, key_expansion, encryption

def convert_num_to_hex_str(unprocessed, reverse=True, base=2):
    """Convert a number in a given base to a 32 characters long hex string.
    If reverse is True, the byte order for the result is reversed.
    
    Parameters:
    unprocessed (cocotb LogicArray): input to be processed
    reverse (boolean): determines whether byte order should be reversed
    base (int): base used to represent the numbers in the input

    Returns:
    res (String): Input converted to a hex string
    """
    hex_encoded = hex(int(str(unprocessed),base))
    padded = (34 - len(hex_encoded)) * "0" + hex_encoded[2:]
    list_hex = [padded[i:i+2] for i in range(0, len(padded),2)]
    if reverse:
        res_list = list(reversed(list_hex))
    else:
        res_list = list_hex
    res = ''.join(res_list)
    return res

def create_input_blocks(aes_in_str):
    """Split hex string into list of of ints with each element
    representing one byte
    """
    aes_in = [int(aes_in_str[i:i+2],16) for i in range(0, len(aes_in_str), 2)]
    return aes_in

def int_list_to_hex_str(int_list, reverse=False):
    """Convert list of ints to hex string where each element of the list
    is interpreted as one byte. If reverse is True, the byte order is reversed.
    """
    if reverse:
        in_list = list(reversed(int_list))
    else:
        in_list = int_list
    hex_str = ""
    for num in in_list:
        hex_n = hex(num)[2:]
        if len(hex_n) < 2:
            hex_n = "0" + hex_n
        hex_str += hex_n
    return hex_str

def create_reference_input(in_value):
    hex_in = convert_num_to_hex_str(in_value, reverse=True, base=10)
    ref_in = create_input_blocks(hex_in)
    return ref_in


@cocotb.test()
async def check_full_encryption(dut):
    # load random input
    input_value = random.randrange(16**32)
    aes_in = create_input_blocks(convert_num_to_hex_str(input_value, reverse=False, base=10))
    
    # get reference output
    key = "2B7E151628AED2A6ABF7158809CF4F3C"
    round_keys = key_expansion(create_input_blocks(key))
    enc_res = encryption(aes_in, round_keys)
    right_enc = int_list_to_hex_str(enc_res)
    
    # generate a clock
    cocotb.start_soon(Clock(dut.aes_module_inst.clk, 1, units="ns").start())
    
    # reset DUT 
    dut.aes_module_inst.rst.value = 1
    for _ in range(2):
        await RisingEdge(dut.aes_module_inst.clk)
    dut.aes_module_inst.rst.value = 0
    
    # start encryption
    for cnt in range(16):
        await RisingEdge(dut.aes_module_inst.clk)
        dut.rx_ready.value = 1
        dut.data_from_rx.value = aes_in[cnt]
    dut.rx_ready.value = 1

    # wait for output
    try:
        await with_timeout(RisingEdge(dut.aes_module_inst.aes_done), 1000, 'ns')
    except SimTimeoutError:
        assert False, "Timeout while waiting on the done signal."
    # get output
    aes_out = convert_num_to_hex_str(dut.aes_module_inst.aes_dout.value, reverse=True, base=2)
    assert aes_out == right_enc

@cocotb.test()
async def check_subbytes(dut):
    # load input
    subbytes_in = random.randrange(16**32)
    dut_subbytes = dut.aes_module_inst.aes_inst.subbytes_inst
    
    # get reference output
    ref_in = create_reference_input(subbytes_in)
    ref_subbytes = int_list_to_hex_str(subbytes(ref_in))
    
    # generate a clock
    cocotb.start_soon(Clock(dut_subbytes.clk, 1, units="ns").start())

    # reset DUT
    dut_subbytes.rst.value = 1

    # reset the module, wait 2 rising edges until we release reset
    for _ in range(2):
        await RisingEdge(dut_subbytes.clk)
    dut_subbytes.rst.value = 0
    
    # set input 
    dut_subbytes.state_in.value = Force(subbytes_in)
    await RisingEdge(dut_subbytes.clk)

    # start operation
    dut_subbytes.ena.value = 1
    
    # wait until operation is done
    try:
        await with_timeout(RisingEdge(dut_subbytes.done), 1000, 'ns')
    except SimTimeoutError:
        assert False, "Timeout while waiting on the done signal."
    
    # check output
    subbytes_out = convert_num_to_hex_str(dut_subbytes.state_out.value, reverse=True)
    assert subbytes_out == ref_subbytes
    dut_subbytes.state_in.value = Release()

@cocotb.test()
async def check_shiftrow(dut):
    # load input
    shiftrows_in = random.randrange(16**32)
    dut_shiftrows = dut.aes_module_inst.aes_inst.shiftrows_inst
    
    # get reference output
    ref_in = create_reference_input(shiftrows_in)
    ref_shiftrows = int_list_to_hex_str(shiftrows(ref_in), reverse=True)

    # generate a clock
    cocotb.start_soon(Clock(dut_shiftrows.clk, 1, units="ns").start())

    # reset DUT
    dut_shiftrows.rst.value = 1

    # reset the module, wait 2 rising edges until we release reset
    for _ in range(2):
        await RisingEdge(dut_shiftrows.clk)
    dut_shiftrows.rst.value = 0

    # set input 
    dut_shiftrows.state_in.value = Force(shiftrows_in)
    await RisingEdge(dut_shiftrows.clk)

    # start operation
    dut_shiftrows.ena.value = 1
    
    try:
        await with_timeout(RisingEdge(dut_shiftrows.done), 1000, 'ns')
    except SimTimeoutError:
        assert False, "Timeout while waiting on the done signal."

    # compare outputs
    shiftrows_out = convert_num_to_hex_str(dut_shiftrows.state_out.value, reverse=False)
    assert shiftrows_out == ref_shiftrows
    dut_shiftrows.state_in.value = Release()

@cocotb.test()
async def check_mixcolumns(dut):
    # load input
    mixcolumns_in = random.randrange(16**32) 
    dut_mixcolumns = dut.aes_module_inst.aes_inst.mixcolumns_inst
    
    # get reference output
    ref_in = create_reference_input(mixcolumns_in)
    ref_mixcolumns = int_list_to_hex_str(mixcolumns(ref_in), reverse=True)

    # generate a clock
    cocotb.start_soon(Clock(dut_mixcolumns.clk, 1, units="ns").start())

    # reset DUT
    dut_mixcolumns.rst.value = 1

    # reset the module, wait 2 rising edges until we release reset
    for _ in range(2):
        await RisingEdge(dut_mixcolumns.clk)
    dut_mixcolumns.rst.value = 0

    # set input 
    dut_mixcolumns.state_in.value = Force(mixcolumns_in)

    try:
        await with_timeout(RisingEdge(dut_mixcolumns.done), 1000, 'ns')
    except SimTimeoutError:
        assert False, "Timeout while waiting on the done signal."

     # start operation
    dut_mixcolumns.ena.value = 1

    # compare output
    mixcolumns_out = convert_num_to_hex_str(dut_mixcolumns.state_out.value, reverse=False)
    assert mixcolumns_out == ref_mixcolumns
    dut_mixcolumns.state_in.value = Release()

@cocotb.test()
async def check_keysched(dut):
    # load input
    key_in = random.randrange(16**32)
    dut_keysched = dut.aes_module_inst.aes_inst.keysched_inst
    
    # get reference outputs
    master_key = create_reference_input(key_in)
    r_keys = int_list_to_hex_str(key_expansion(master_key))
    round_keys = []
    for i in range(11):
        round_keys.append(r_keys[i*32:(i+1)*32])
    #print(f"round keys: {round_keys})
    
    # generate a clock
    cocotb.start_soon(Clock(dut_keysched.clk, 1, units="ns").start())

    # reset DUT
    dut_keysched.rst.value = 1

    # reset the module, wait 2 rising edges until we release reset
    for _ in range(2):
        await RisingEdge(dut_keysched.clk)
    dut_keysched.rst.value = 0

    # check all round keys
    for i in range(1,11):
        # set input 
        dut_keysched.prev_key_in.value = Force(key_in)
        dut_keysched.round_in.value = Force(i)
        await RisingEdge(dut_keysched.clk)

        # start operation
        dut_keysched.ena.value = 1
        
        key_out = convert_num_to_hex_str(dut_keysched.next_key_out.value, reverse=True)
        key_in = dut_keysched.next_key_out.value

        assert key_out == round_keys[i]
    
@cocotb.test()
async def check_addkey(dut):
    dut_aes = dut.aes_module_inst.aes_inst

    # generate a clock
    cocotb.start_soon(Clock(dut_aes.clk, 1, units="ns").start())

    # reset DUT
    dut_aes.rst.value = 1

    # reset the module, wait 2 rising edges until we release reset
    for _ in range(2):
        await RisingEdge(dut_aes.clk)
    dut_aes.rst.value = 0

    # set input 
    state = 0
    dut_aes.aes_state.value = Force(0)
    await RisingEdge(dut_aes.clk)
    dut_aes.aes_state.value = Release()
    dut_aes.fsm_state.value = Force(-3)
    
    random_key = random.randrange(16**32)
    dut_aes.key.value = Force(random_key)
    
    # wait for two clock cycles
    await RisingEdge(dut_aes.clk)
    await RisingEdge(dut_aes.clk)
    # check output
    aes_state = dut_aes.aes_state.value
    assert aes_state == random_key


