#!/usr/bin/env bash

MYDIR="${0%/*}"

sphinx-build -b html docs $MYDIR/../dist/docs
