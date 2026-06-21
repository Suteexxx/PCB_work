"""
Generates a handful of realistic-looking (but synthetic/dummy) datasheet
PDFs into backend/data/sample_datasheets/, purely so the KB ingestion +
query pipeline can be tested end-to-end offline, without needing real
copyrighted manufacturer datasheets.

Run once:
    python scripts/generate_sample_datasheets.py

NOTE: These are illustrative technical documents written for testing
purposes, not reproductions of any real manufacturer's datasheet content.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

from app.core.config import get_settings


def _build_pdf(path: Path, title: str, subtitle: str, sections: list[tuple[str, str]], spec_table: list[list[str]]):
    doc = SimpleDocTemplate(
        str(path), pagesize=LETTER, topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        title=title, author="PCB Research Agent (synthetic test data)",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleX", parent=styles["Title"], fontSize=18)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6)
    body = ParagraphStyle("BodyX", parent=styles["BodyText"], leading=15)

    story = [Paragraph(title, title_style), Paragraph(subtitle, styles["Heading3"]), Spacer(1, 16)]

    if spec_table:
        t = Table(spec_table, colWidths=[2.3 * inch, 2.3 * inch, 2.0 * inch])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f7")]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story += [t, Spacer(1, 18)]

    for heading, text in sections:
        story.append(Paragraph(heading, h2))
        story.append(Paragraph(text, body))
        story.append(Spacer(1, 6))

    doc.build(story)
    print(f"  wrote {path}")


def generate_zero_drift_opamp_datasheet(out_dir: Path):
    _build_pdf(
        out_dir / "ZD-OPX100_zero_drift_opamp_datasheet.pdf",
        "ZD-OPX100 — Zero-Drift, Chopper-Stabilized Operational Amplifier",
        "Synthetic test datasheet for KB ingestion pipeline validation",
        spec_table=[
            ["Parameter", "Value", "Condition"],
            ["Offset Voltage (Vos)", "1 uV typ, 5 uV max", "TA = 25C"],
            ["Offset Voltage Drift", "0.005 uV/C", "-40C to 125C"],
            ["Input Voltage Noise Density", "11 nV/sqrt(Hz)", "f = 1kHz"],
            ["1/f Noise Corner", "Not applicable (chopped)", "Auto-zero architecture"],
            ["Gain Bandwidth Product", "2.8 MHz", "typical"],
            ["Quiescent Current", "1.2 mA per amplifier", "typical"],
            ["Supply Voltage Range", "2.7V to 5.5V single supply", "or +/-1.35V to +/-2.75V dual"],
            ["CMRR", "140 dB typical", "DC"],
            ["PSRR", "140 dB typical", "DC"],
        ],
        sections=[
            (
                "1. General Description",
                "The ZD-OPX100 is a zero-drift operational amplifier that uses a chopper "
                "stabilization technique to continuously cancel input offset voltage and "
                "1/f noise. Unlike conventional auto-zero architectures that sample and "
                "hold, the chopper topology modulates the input signal above the flicker "
                "noise corner, amplifies it, and demodulates it back to baseband, "
                "resulting in extremely low offset voltage drift over temperature and "
                "time. This makes the device well suited for precision instrumentation "
                "amplifiers, current sense amplifiers, and ultra low noise current source "
                "designs where long term stability is critical.",
            ),
            (
                "2. Noise Performance",
                "Input voltage noise density is specified at 11 nV per square root Hz at "
                "1 kHz, with no 1/f noise corner due to the chopping architecture. When "
                "used in a current source feedback loop, the dominant noise contribution "
                "typically shifts to the sense resistor's Johnson noise and the reference "
                "voltage noise rather than the amplifier itself, provided the sense "
                "resistor value and bandwidth are chosen appropriately. Designers building "
                "ultra low noise current sources should budget total output current noise "
                "as the root sum square of amplifier voltage noise divided by the sense "
                "resistance, resistor thermal noise, and reference noise contributions.",
            ),
            (
                "3. Application: Precision Current Source",
                "In a Howland or modified Howland current pump topology, the ZD-OPX100's "
                "extremely low offset voltage and drift directly translate into excellent "
                "current source accuracy and stability over temperature, since any "
                "amplifier input offset appears as a current error proportional to the "
                "sense resistor value. For best results, pair this amplifier with "
                "ultra-precision, low temperature coefficient resistors in the gain "
                "network to preserve the matching accuracy the topology depends on.",
            ),
            (
                "4. Power Supply Recommendations",
                "The ZD-OPX100 operates from a single 2.7V to 5.5V supply or a dual "
                "symmetrical supply. For best noise and PSRR performance, supply rails "
                "should be locally decoupled with a 0.1uF ceramic capacitor placed close "
                "to the supply pins, in addition to a bulk 10uF capacitor per supply rail. "
                "When deriving bipolar rails from a single DC input, a low noise inverting "
                "charge pump or a small auxiliary LDO-based negative rail generator is "
                "recommended to avoid injecting switching noise into the signal path.",
            ),
        ],
    )


def generate_precision_resistor_datasheet(out_dir: Path):
    _build_pdf(
        out_dir / "PRX-Foil-Series_ultra_precision_resistor_datasheet.pdf",
        "PRX-Foil Series — Ultra-Precision Bulk Metal Foil Resistors",
        "Synthetic test datasheet for KB ingestion pipeline validation",
        spec_table=[
            ["Parameter", "Value", "Condition"],
            ["Resistance Tolerance", "0.01% (100 ppm)", "standard grade"],
            ["Temperature Coefficient (TCR)", "0.2 ppm/C typical", "-55C to 125C"],
            ["Long Term Stability", "25 ppm / year typical", "rated power, 25C"],
            ["Voltage Coefficient", "< 0.1 ppm/V", "negligible nonlinearity"],
            ["Thermal EMF", "< 0.05 uV/C", "low thermoelectric error"],
            ["Power Rating", "0.3W to 0.6W", "package dependent"],
            ["Current Noise Index", "< -40 dB", "extremely low excess noise"],
        ],
        sections=[
            (
                "1. General Description",
                "The PRX-Foil series are bulk metal foil resistors designed for "
                "applications demanding the highest levels of precision and long term "
                "stability. The foil resistive element exhibits near zero temperature "
                "coefficient of resistance and extremely low current noise compared to "
                "thin film or thick film resistor technologies, making this series the "
                "preferred choice for precision current sense applications, voltage "
                "references, and gain-setting networks in low noise instrumentation.",
            ),
            (
                "2. Why Resistor Selection Matters for Current Sources",
                "In a precision current source, the sense or gain resistor directly sets "
                "output current accuracy and contributes Johnson thermal noise to the "
                "total output noise budget. A resistor with high temperature coefficient "
                "will cause current drift over temperature even if the amplifier and "
                "reference are ideal. Selecting an ultra-precision foil resistor with sub "
                "1 ppm/C TCR for the critical gain-setting resistors in a Howland or "
                "Libbrecht-Hall style current pump significantly improves both the "
                "absolute accuracy and the temperature stability of the generated current.",
            ),
            (
                "3. Matching and Tracking",
                "For topologies that rely on resistor ratio matching, such as the "
                "Howland current pump, using resistors from the same production batch or "
                "a matched resistor network array improves ratio tracking far beyond what "
                "individual tolerance specifications alone would suggest, because "
                "correlated drift between matched elements cancels in the ratio.",
            ),
        ],
    )


def generate_ldo_datasheet(out_dir: Path):
    _build_pdf(
        out_dir / "LDX-3300_low_noise_LDO_datasheet.pdf",
        "LDX-3300 — Ultra-Low-Noise, High PSRR Linear Regulator (LDO)",
        "Synthetic test datasheet for KB ingestion pipeline validation",
        spec_table=[
            ["Parameter", "Value", "Condition"],
            ["Output Voltage Noise", "9.5 uVrms", "10Hz to 100kHz"],
            ["PSRR", "70 dB", "f = 10kHz"],
            ["Dropout Voltage", "120 mV", "at 200mA load"],
            ["Output Current", "up to 300 mA", "continuous"],
            ["Quiescent Current", "55 uA", "no load"],
            ["Line Regulation", "0.02 %/V", "typical"],
            ["Load Regulation", "0.04 %", "typical"],
        ],
        sections=[
            (
                "1. General Description",
                "The LDX-3300 is an ultra-low-noise linear regulator intended for "
                "powering noise-sensitive analog circuitry such as precision references, "
                "instrumentation amplifiers, and current source front ends. Its low "
                "dropout architecture allows efficient regulation from a single DC input "
                "rail while keeping output voltage noise below 10 microvolts RMS across "
                "the 10 Hz to 100 kHz band, which is critical for not degrading the noise "
                "floor of downstream zero-drift amplifier stages.",
            ),
            (
                "2. Generating Multiple Rails from a Single DC Input",
                "For designs that must operate from a single DC supply but require a "
                "regulated positive rail, a regulated negative rail, and a clean voltage "
                "reference, a common architecture uses one LDX-3300 for the positive "
                "analog rail, a charge-pump-based or inverting switching regulator "
                "followed by a second LDX-3300 to generate a clean negative rail, and a "
                "dedicated low noise reference IC for the precision voltage reference. "
                "This approach isolates noisy switching elements from the precision "
                "signal path while still allowing fully single-supply system operation.",
            ),
            (
                "3. Decoupling and PCB Layout",
                "Place the input and output decoupling capacitors as close as possible "
                "to the LDX-3300 pins, with a low ESR ceramic capacitor of at least 1uF "
                "on the output to maintain loop stability and minimize output noise. "
                "Keep the ground return path for the regulator separate from sensitive "
                "analog ground traces where possible, using a star-ground or partitioned "
                "ground plane strategy on the PCB.",
            ),
        ],
    )


def main():
    settings = get_settings()
    out_dir = settings.sample_datasheets_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating sample datasheets into {out_dir} ...")
    generate_zero_drift_opamp_datasheet(out_dir)
    generate_precision_resistor_datasheet(out_dir)
    generate_ldo_datasheet(out_dir)
    print("Done. Run scripts/ingest_datasheets.py next to index them.")


if __name__ == "__main__":
    main()
