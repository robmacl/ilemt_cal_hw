# Trio Support Inquiry — MC508 P849

**Controller:** MC508 P849 · firmware (`VERSION`) 2.0316 · `FPGA_VERSION` 11

## Question

We want to run **two stepper drives (step + direction only, no extra features)
off a single flexible-axis connector** — i.e. use both the primary axis and
the second (n+8) axis on the same 20-pin connector for pulse+direction output.

At the same time, on *other* connectors we use **encoder inputs and need the Z
(index) input** on those connectors.

How do we configure this?

## What we tried

- Standard stepper ATYPE 43 on the axes: the primary axis works, but the
  second (n+8) axis produces **no step pulses** (connector pins 11/12 sit
  static-high — they appear to be the primary axis's enable output).
- High-density stepper ATYPE 100 on the stepper axes, with ATYPE 76 encoders
  on the other connectors: after power cycle, `?ATYPE` reads 100 but the
  startup banner reports **"Stepper Axes : None"** — the steppers don't come
  up. (Encoders 0–3 still report as encoder axes.)

So our open question is whether two pulse+direction axes can share one
connector **while** other connectors run ATYPE-76 encoders with a working Z
index — and if so, the correct ATYPE / configuration to use.
