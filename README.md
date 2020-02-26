# Learning nMigen with a UART Module

I recently learned about a project called ["Migen"](https://github.com/m-labs/migen/) from a [blog post written by WhiteQuark](https://lab.whitequark.org/notes/2016-10-18/implementing-an-uart-in-verilog-and-migen/). It looks like Migen is a Python library which aims to provide a simpler way to write hardware description logic that can compile down to VHDL or Verilog.

But it turns out that the Migen team has been hard at work since 2016, and now there is a newer version of the project called ["nMigen"](https://github.com/m-labs/nmigen/). It makes some breaking API changes, but it looks like a big improvement in terms of legibility and core functionality.

So I decided to try to learn how to use nMigen by writing a simple UART module. I've only got a barebones receiver working so far, but I am finding it much easier to write and debug than VHDL or Verilog.

I also haven't quite figured out how to connect the `rx` and `tx` signals to actual pins on a real FPGA. I'm hoping to get some ICE40LP384 boards which I can use for testing soon, but for now, this module will only run in the testbench simulation.

# Further Reading

There are already two example projects in the "nMigen" repository which implement UART modules; those are probably better references, but I'm writing this as a learning exercise.

https://github.com/m-labs/nmigen/blob/master/examples/basic/uart.py

https://github.com/m-labs/nmigen/blob/master/examples/basic/fsm.py

The "LambdaConcept" blog / wiki has a few tutorials which introduce nMigen's basic syntax and usage:

http://blog.lambdaconcept.com/doku.php?id=nmigen:tutorial

Unfortunately, I haven't been able to find a comprehensive API reference for nMigen yet. But overall, my impressions are very positive :)
