"""Currencies the panel knows: the ISO 4217 codes the exchange rate source covers (166, 23.11.2026).

The organization currency must be one of them. The list is static, so the
setup works before the first rate download (or offline). A currency without
a stored rate is still valid; its amounts are shown unconverted.
"""

import re

_CODES = """
AED AFN ALL AMD ANG AOA ARS AUD AWG AZN BAM BBD BDT BGN BHD BIF BMD BND BOB BRL BSD BTN BWP BYN BZD
CAD CDF CHF CLF CLP CNH CNY COP CRC CUP CVE CZK DJF DKK DOP DZD EGP ERN ETB EUR FJD FKP FOK GBP GEL
GGP GHS GIP GMD GNF GTQ GYD HKD HNL HRK HTG HUF IDR ILS IMP INR IQD IRR ISK JEP JMD JOD JPY KES KGS
KHR KID KMF KRW KWD KYD KZT LAK LBP LKR LRD LSL LYD MAD MDL MGA MKD MMK MNT MOP MRU MUR MVR MWK MXN
MYR MZN NAD NGN NIO NOK NPR NZD OMR PAB PEN PGK PHP PKR PLN PYG QAR RON RSD RUB RWF SAR SBD SCR SDG
SEK SGD SHP SLE SLL SOS SRD SSP STN SYP SZL THB TJS TMT TND TOP TRY TTD TVD TWD TZS UAH UGX USD UYU
UZS VES VND VUV WST XAF XCD XCG XDR XOF XPF YER ZAR ZMW ZWG ZWL
"""

KNOWN_CURRENCIES: frozenset[str] = frozenset(_CODES.split())
CODE = re.compile(r"^[A-Z]{3}$")


def is_known(code: str) -> bool:
    return code in KNOWN_CURRENCIES
