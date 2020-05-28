# -*- coding: utf-8 -*-
# Copyright (c) 2019 Civic Knowledge. This file is licensed under the terms of the
# MIT License, included in this distribution as LICENSE

"""



"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import collections
from cityiq.iterate import EventIterator
from cityiq.util import grouper

from .api import CityIqObject

logger = logging.getLogger(__name__)


