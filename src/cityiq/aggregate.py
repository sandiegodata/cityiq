# -*- coding: utf-8 -*-
# Copyright (c) 2019 Civic Knowledge. This file is licensed under the terms of the
# MIT License, included in this distribution as LICENSE
"""
Aggregate events by location and type into CSV files.


"""

import asyncio
import itertools
import json
import logging
from pathlib import Path
from time import sleep

from .api import CityIq

logger = logging.getLogger(__name__)

