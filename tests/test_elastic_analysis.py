import pytest
from elastic_analysis import calc_mechanical_properties, parse_elastic_output


def test_mechanical_properties_pure_w():
    # Approximate values for tungsten
    C11, C12, C44 = 523.0, 205.0, 161.0
    props = calc_mechanical_properties(C11, C12, C44)

    B = (C11 + 2 * C12) / 3.0
    assert props['B'] == pytest.approx(B, rel=1e-6)

    G_V = (C11 - C12 + 3 * C44) / 5.0
    G_R = 5 * (C11 - C12) * C44 / (4 * C44 + 3 * (C11 - C12))
    G = (G_V + G_R) / 2.0
    assert props['G_V'] == pytest.approx(G_V, rel=1e-6)
    assert props['G_R'] == pytest.approx(G_R, rel=1e-6)
    assert props['G_VRH'] == pytest.approx(G, rel=1e-6)

    E = 9 * B * G / (3 * B + G)
    assert props['E'] == pytest.approx(E, rel=1e-6)

    nu = (3 * B - 2 * G) / (2 * (3 * B + G))
    assert props['nu'] == pytest.approx(nu, rel=1e-6)

    assert props['B_G_ratio'] == pytest.approx(B / G, rel=1e-6)
    assert props['Cauchy'] == pytest.approx(C12 - C44, rel=1e-6)

    A = 2 * C44 / (C11 - C12)
    assert props['A'] == pytest.approx(A, rel=1e-6)

    k = G / B
    Hv = 2 * (k**2 * G)**0.585 - 3
    assert props['Hv'] == pytest.approx(Hv, rel=1e-6)


def test_mechanical_properties_keys():
    props = calc_mechanical_properties(500, 200, 150)
    expected_keys = {'B', 'G_V', 'G_R', 'G_VRH', 'E', 'nu',
                     'B_G_ratio', 'Cauchy', 'A', 'Hv'}
    assert set(props.keys()) == expected_keys


def test_parse_elastic_output():
    output = """
***cubic_elastic_constants***

DFT_0001

sws(bohr)      =   2.941
B(GPa)         = 321.30
c11(GPa)       = 523.10
c12(GPa)       = 205.40
c'(GPa)        = 158.85
c44(GPa)       = 161.20
R-squared(c')  = 0.999800
R-squared(c44) = 0.999500

Voigt average:

BV(GPa)  = 311.30
GV(GPa)  = 159.42
EV(GPa)  = 410.50
vV(GPa)  =   0.29

Reuss average:

BR(GPa)  = 311.30
GR(GPa)  = 158.20
ER(GPa)  = 408.30
vR(GPa)  =   0.29

Hill average:

BH(GPa)  = 311.30
GH(GPa)  = 158.81
EH(GPa)  = 409.40
vH(GPa)  =   0.29

Elastic anisotropy:

AVR(GPa)  =   0.00
"""
    result = parse_elastic_output(output)
    assert result['C11'] == pytest.approx(523.10)
    assert result['C12'] == pytest.approx(205.40)
    assert result['C44'] == pytest.approx(161.20)
    assert result['cprime'] == pytest.approx(158.85)
    assert result['B'] == pytest.approx(321.30)
