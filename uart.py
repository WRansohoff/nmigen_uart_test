from nmigen import *
from nmigen.back.pysim import *

# Function to calculate a clock divider which creates the
# desired output frequency from a given input frequency.
# Verifies that the divider is a positive integer, and that
# the resulting signal doesn't deviate more than expected.
def clock_divider( inf, outf, max_err ):
  # Calculate the divisor.
  div = inf // outf
  # Check that the rounded clock divider is a positive integer.
  if div < 1:
    print( "Error: Invalid input / output frequencies to " +
           "clock divider (%d / %d)"
           %( inf, outf ) )
    raise ValueError
  # Check that the error value does not exceed the given threshold.
  err = ( ( inf / div ) - outf ) / outf
  if err > max_err:
    print( "Error: Clock divider error rate is too high " +
           "(%1.2f > %1.2f)"
           %( err, max_err ) )
    raise ValueError
  # Return the divisor.
  return div

# Basic work-in-progress UART modules.
# - TX / RX only, no flow control or USART.
# - Samples during the middle of the clock period, no oversampling.
# - 8-bit words, 1 stop bit, no parity bit.
# - Receives bits LSB-first only.
# - Configurable baud rate.

# UART receiver.
class UART_RX( Elaboratable ):
  def __init__( self, clk_freq, baud_rate ):
    # Calculate the clock divider for the given frequency / baud rate.
    self.clk_div = clock_divider( clk_freq, baud_rate, 0.05 )
    # Signals with external connections.
    self.rx        = Signal()
    # Internal signals.
    self.rx_count  = Signal( range( self.clk_div ) )
    self.rx_buf    = Signal( 8 )
    self.rx_bit    = Signal( 3 )
    self.rx_ack    = Signal()
    self.rx_fix    = Signal()
    self.rx_strobe = Signal()

  def elaborate( self, platform ):
    m = Module()

    # Increment the RX counter each clock edge.
    with m.If( self.rx_count == self.clk_div - 1 ):
      m.d.sync += self.rx_count.eq( 0 )
    with m.Else():
      m.d.sync += self.rx_count.eq( self.rx_count + 1 )
    # Toggle the "rx_strobe" value whenever "rx_count" ticks over.
    m.d.comb += self.rx_strobe.eq( self.rx_count == 0 )

    # RX state machine.
    with m.FSM() as fsm:
      # RX state machine: "Idle" state.
      # - Move to the "Start" state when the "RX" line goes low.
      #   - Set the "rx_count" value to half of the clock divider, so
      #     that bits are sampled in the middle of each clock period.
      #   - Reset the other peripheral signals.
      with m.State( "RX_IDLE" ):
        with m.If( ~self.rx ):
          m.next = "RX_START"
          m.d.sync += [
            self.rx_ack.eq( 0 ),
            self.rx_fix.eq( 0 ),
            self.rx_bit.eq( 0 ),
            self.rx_buf.eq( 0x00 ),
            self.rx_count.eq( self.clk_div // 2 )
          ]
      # RX state machine: "Start" state.
      # - Wait half a cycle until the clock divider ticks over, then
      #   move to the "Data" state.
      with m.State( "RX_START" ):
        with m.If( self.rx_strobe ):
          m.next = "RX_DATA"
      # RX state machine: "Data" state.
      # - Wait one cycle, then prepend the RX bit and move to the
      #   "Stop" state iff 8 bits have been received.
      with m.State( "RX_DATA" ):
        with m.If( self.rx_strobe ):
          m.d.sync += [
            self.rx_buf.eq( Cat( self.rx_buf[ 1 : 8 ], self.rx ) ),
            self.rx_bit.eq( self.rx_bit + 1 )
          ]
          with m.If( self.rx_bit == 7 ):
            m.next = "RX_STOP"
      # RX state machine: "Stop" state.
      # - Wait one cycle, then move to the "Full" state if the
      #   "RX" line is asserted and to the "Error" state if not.
      with m.State( "RX_STOP" ):
        with m.If( self.rx_strobe ):
          with m.If( self.rx ):
            m.next = "RX_FULL"
          with m.Else():
            m.next = "RX_ERROR"
      # RX state machine: "Full" state.
      # - Wait for an external "rx_ack" signal to indicate that the
      #   value has been read, then move to the "Idle" state.
      # - Move to the "Error" state if a start bit is detected before
      #   an "rx_ack" signal is received.
      with m.State( "RX_FULL" ):
        with m.If( self.rx_ack ):
          m.next = "RX_IDLE"
        with m.Elif( ~self.rx ):
          m.next = "RX_ERROR"
      # RX state machine: "Error" state.
      # - Wait for an external "rx_fix" signal, then return to "Idle".
      with m.State( "RX_ERROR" ):
        with m.If( self.rx_fix ):
          m.next = "RX_IDLE"

    return m

# UART transmitter
class UART_TX( Elaboratable ):
  def __init__( self, clk_freq, baud_rate ):
    # Calculate the clock divider for the given frequency / baud rate.
    self.clk_div = clock_divider( clk_freq, baud_rate, 0.05 )
    # Signals with external connections.
    self.tx        = Signal()
    # TX signals.
    self.tx_count  = Signal( range( self.clk_div ) )
    self.tx_buf    = Signal( 8 )
    self.tx_bit    = Signal( 3 )
    self.tx_fix    = Signal()
    self.tx_strobe = Signal()

  def elaborate( self, platform ):
    m = Module()

    # Increment the TX counter each clock edge.
    with m.If( self.tx_count == self.clk_div - 1 ):
      m.d.sync += self.tx_count.eq( 0 )
    with m.Else():
      m.d.sync += self.tx_count.eq( self.tx_count + 1 )
    # Toggle the "tx_strobe" value whenever "tx_count" ticks over.
    m.d.comb += self.tx_strobe.eq( self.tx_count == 0 )

    # TODO: TX module state machine.

    return m

# Combined UART interface with both TX and RX modules.
class UART( Elaboratable ):
  def __init__( self, uart_rx, uart_tx ):
    self.uart_rx = uart_rx
    self.uart_tx = uart_tx

  def elaborate( self, platform ):
    m = Module()
    m.submodules.rx = self.uart_rx
    m.submodules.tx = self.uart_tx
    return m

#
# Simple UART testbench.
#

# Helper UART test method to simulate receiving a byte.
def uart_rx_byte( uart, val ):
  # Simulate a "start bit".
  yield uart.rx.eq( 0 )
  # Wait one cycle.
  for i in range( uart.clk_div ):
    yield Tick()
  # Simulate the byte with one cycle between each bit.
  for i in range( 8 ):
    if val & ( 1 << i ):
      yield uart.rx.eq( 1 )
    else:
      yield uart.rx.eq( 0 )
    for j in range( uart.clk_div ):
      yield Tick()
  # Simulate the "stop bit", and wait one cycle.
  yield uart.rx.eq( 1 )
  for i in range( uart.clk_div ):
    yield Tick()

# UART 'receive' testbench.
def uart_rx_test( uart_rx ):
  # Simulate receiving "0xAF".
  yield from uart_rx_byte( uart_rx, 0xAF )
  # Wait a couple of cycles, then send "rx_ack".
  for i in range( uart_rx.clk_div * 2 ):
    yield Tick()
  yield uart_rx.rx_ack.eq( 1 )
  # Simulate receiving "0x42".
  yield from uart_rx_byte( uart_rx, 0x42 )
  # Simulate receiving "0x24" (should cause an error)
  yield from uart_rx_byte( uart_rx, 0x24 )
  # Wait a cycle, then send the "fix" signal and re-send 0x24.
  for i in range( uart_rx.clk_div ):
    yield Tick()
  yield uart_rx.rx_fix.eq( 1 )
  yield from uart_rx_byte( uart_rx, 0x24 )
  # Send "rx_ack" and wait a cycle to see the end state.
  yield uart_rx.rx_ack.eq( 1 )
  for i in range( uart_rx.clk_div ):
    yield Tick()

# UART 'transmit' testbench.
def uart_tx_test( uart_tx ):
  # TODO
  yield Tick()

# Create a UART module and run tests on it.
# (The baud rate is set to a high value to speed up the simulation.)
if __name__ == "__main__":
  #uart_rx = UART_RX( 24000000, 9600 )
  #uart_tx = UART_TX( 24000000, 9600 )
  uart_rx = UART_RX( 24000000, 1000000 )
  uart_tx = UART_TX( 24000000, 1000000 )
  uart    = UART( uart_rx, uart_tx )

  # Run the UART tests.
  with Simulator( uart, vcd_file = open( 'test.vcd', 'w' ) ) as sim:
    def proc_rx():
      yield from uart_rx_test( uart.uart_rx )
    def proc_tx():
      yield from uart_tx_test( uart.uart_tx )

    # Run the UART test with a 24MHz clock.
    sim.add_clock( 24e-6 )
    sim.add_sync_process( proc_rx )
    sim.add_sync_process( proc_tx )
    sim.run()
