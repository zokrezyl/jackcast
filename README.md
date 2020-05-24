# Jack Cast, the storry

A simple tool to transmit Jack audio and Midi over the network.

The tool is still under work, but already solves it's original purposes

## Why a new tool or why reinventing the wheel?

There were two problems I tried to solve originally:
* send audio and midi between Linux and Windows hosts. While the existing tools are doing great job, they proved to have limitations and it turned out to be useless for my use-case.
* send Midi signal between Windows and Linux

While the original purpose was to send audio to/from windows, it wants to be a good alternative for Linux only.

Please read the story to understand the limitations of the existing tools and what JackCast tries to do better.

## Original Usecase/requirements
* Runnig Steinberg Cubase on a windows host
* Send audio out of Cubase to a Jack Audio Server running on another linux host
* Do all this with the smallest latency without compromising audio quality
* Feed Cubase with Midi signal comming from a device attached to the linux host

## Class of problems encountered with the existing solutions
* Default multicast is blocked by switches (net jack)
* Difficult to setup (net jack, jack.trip)
* Not available on windows (zita-j2n)
* Depending on other tools/drivers (jack.trip needs ASIO4ALL)
* introducing XRUNS at not yet so low latency settings

## What JackCast can do better
* Can run with the dummy driver, thus latency and other timings are not influenced by useless drivers like AIO4ALL
* Easy to extend, debug, troubleshoot (python)
* Adaptive latency on the reciever (some details still under work)


## TODO's
* unify the protocol for midi audio 
* add support for OSC


# How to use it

## Setup

### Linux

### Windows


## Usage

