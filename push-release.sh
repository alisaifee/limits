#!/bin/bash
cur=$(git rev-parse --abbrev-ref HEAD)
git checkout 4.x
git push origin 4.x --tags
git checkout $cur
