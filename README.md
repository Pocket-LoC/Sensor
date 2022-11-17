# Pocket-LoC
<img align = "right" src="https://user-images.githubusercontent.com/42568983/202521498-0bb95a05-1dd4-4db9-ad12-fc51b9aba1ed.jpg" width="40%" /> 
Lab-on-chip (LoC) technology is becoming increasingly relevant, especially in the field of medicine. However, often LoC setups rely on complex lab equipment for operation. The aim of this project is to create an affordable and portable LoC setup as a proof-of-concept for truly pocket-sized LoC - the Pocket LoC.

Pocket LoC can be assembled with standard equipment found in a typcial engineering lab (such as a maker space or FabLab). Once assembled, Pocket LoC is fully portable and only needs a PC to operate.

## Sensor
The sensor contains two spectral sensors ([AS7341](https://ams.com/en/as7341) from AMS) and a microcontroller (Atmel ATmega32U4) for operation. A second PCB with two LEDs as light sources is connected via a flat flexible cable (FFC), and also driven by the microcontroller. The sensor can be operated like an Arduino with connected peripherals, making coding simple.

## PCB assembly
All design files for the PCB can be found as an Altium project in the "hardware" folder. You can order the ready printed PCB from manufacturers like [JLCPCB](https://jlcpcb.com/) or [multi-cb](https://www.multi-circuit-boards.eu/en/index.html) and assemble it yourself (requires tools and skills for SMD assembly), order an assembled PCB or contact me.

Once assembled, the microcontroller will have to be initially flashed with a bootloader (requires an ISP device, e.g. an Arduino) and then can be programmed and used via a regular USB connection. 

### Flashing Bootloader

## Firmware
