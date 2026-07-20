from config import ELEMENT_SWS

def calc_vegard_sws(composition):
    if not composition:
        raise ValueError("composition must not be empty")
    total = sum(composition.values())
    if abs(total - 100.0) > 0.5:
        raise ValueError(f"concentrations sum to {total}, expected 100")
    sws = 0.0
    for elem, conc in composition.items():
        sws += (conc / 100.0) * ELEMENT_SWS[elem]
    return sws
