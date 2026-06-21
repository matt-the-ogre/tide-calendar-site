"""Display-unit helpers for tide heights. Internals stay metric; convert only
for display. 'imperial' -> feet; anything else -> metres."""
_M_TO_FT = 3.28084


def convert(height_m, unit):
    if unit == 'imperial':
        return round(height_m * _M_TO_FT, 1)
    return height_m


def suffix(unit):
    return 'ft' if unit == 'imperial' else 'm'
