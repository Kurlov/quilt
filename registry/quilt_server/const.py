# Copyright (c) 2017 Quilt Data, Inc. All rights reserved.

"""
Constants
"""

from enum import Enum
import re

PUBLIC = 'public' # This username is blocked by Quilt signup
VALID_NAME_RE = re.compile(r'^[a-zA-Z]\w*$', re.UNICODE)
VALID_EMAIL_RE = re.compile(r'^([^\s@]+)@([^\s@]+)$')

class PaymentPlan(Enum):
    FREE = 'free'
    INDIVIDUAL = 'individual_monthly_7'
    BUSINESS_ADMIN = 'business_monthly_490'
    BUSINESS_MEMBER = 'business_member'
