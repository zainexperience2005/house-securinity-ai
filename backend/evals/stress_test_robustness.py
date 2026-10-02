"""Robustness evals: rotate, blur, and downscale PDFs then re-run scrutiny."""
import os
import sys
import json
import time
import tempfile
import pymupdf
from PIL import Image, ImageEnhance, ImageFilter

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.pipeline import run


def create_degraded_pdf(source_pdf_path: str, degradation_type: str, output_path: str):
    """Generates a degraded copy of the source PDF with specific scan/visual noise."""
    doc = pymupdf.open(source_pdf_path)
    out_doc = pymupdf.open()

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        
        # Render page to high-res pixmap first
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Apply specific degradation
        if degradation_type == "rotation_90":
            img = img.rotate(90, expand=True)
        elif degradation_type == "rotation_180":
            img = img.rotate(180, expand=True)
        elif degradation_type == "rotation_270":
            img = img.rotate(270, expand=True)
        elif degradation_type == "low_dpi_scan":
            # Downsample to 72 DPI and upscale back with bilinear blur
            w, h = img.size
            img = img.resize((w // 2, h // 2), Image.Resampling.BILINEAR)
            img = img.resize((w, h), Image.Resampling.NEAREST)
        elif degradation_type == "heavy_noise_grain":
            # Blur + high contrast photocopy simulation
            img = img.filter(ImageFilter.GaussianBlur(radius=1.2))
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.8)
        elif degradation_type == "faded_blueprint":
            # Low contrast faded blueprint
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(0.55)
            brightness = ImageEnhance.Brightness(img)
            img = brightness.enhance(1.15)

        # Save degraded image to temp PNG and reinsert into new PDF
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
            tmp_img_path = tmp_img.name
            img.save(tmp_img_path, format="PNG")

        img_rect = pymupdf.Rect(0, 0, img.width * 72 / 200, img.height * 72 / 200)
        new_page = out_doc.new_page(width=img_rect.width, height=img_rect.height)
        new_page.insert_image(img_rect, filename=tmp_img_path)

        try:
            os.remove(tmp_img_path)
        except Exception:
            pass

    out_doc.save(output_path)
    out_doc.close()
    doc.close()


def run_robustness_suite():
    print("=" * 80)
    print("⚡ HOUSE SCRUTINY AGENT - SCAN NOISE & ROBUSTNESS STRESS TEST")
    print("=" * 80)

    sample_pdf = os.path.join(PROJECT_ROOT, "data", "93-B OPF GROUND FLOOR SLAB STR DWG.pdf")
    if not os.path.exists(sample_pdf):
        print(f"Error: Sample PDF not found at {sample_pdf}")
        return

    degradations = [
        ("clean_baseline", "Baseline Clean PDF", None),
        ("rotation_90", "90-Degree Rotation Shift", "rotation_90"),
        ("rotation_180", "180-Degree Inverted Orientation", "rotation_180"),
        ("rotation_270", "270-Degree Counter-Clockwise Rotation", "rotation_270"),
        ("low_dpi_scan", "Low-DPI Fax/Scanned Compression (100 DPI)", "low_dpi_scan"),
        ("heavy_noise_grain", "High-Contrast Photocopy Noise & Blur", "heavy_noise_grain"),
        ("faded_blueprint", "Faded Blueprint / Low-Contrast Washout", "faded_blueprint"),
    ]

    results = []
    scratch_dir = os.path.join(os.path.dirname(__file__), "stress_artifacts")
    os.makedirs(scratch_dir, exist_ok=True)

    for deg_id, desc, deg_type in degradations:
        print(f"\n▶ Testing Condition: {desc} [{deg_id}]")
        t0 = time.time()
        
        if deg_type is None:
            target_pdf = sample_pdf
        else:
            target_pdf = os.path.join(scratch_dir, f"degraded_{deg_id}.pdf")
            create_degraded_pdf(sample_pdf, deg_type, target_pdf)

        try:
            verdict = run(target_pdf)
            elapsed = round(time.time() - t0, 2)
            
            # Key robustness checks:
            # 1. No Crash
            # 2. Guardrail integrity: Uncertified drawing must NOT be falsely approved
            overall_verdict = verdict.get("overall")
            has_stability_cert = verdict.get("certificate_audit", {}).get("certificate_present", False)
            safety_passed = (overall_verdict in ["CORRECTION_REQUIRED", "PENDING_HUMAN_REVIEW"] and not has_stability_cert)
            
            # 3. Extraction capability
            concrete_psi = verdict.get("structural_analysis", {}).get("concrete_grade_psi")
            slab_thk = verdict.get("structural_analysis", {}).get("slab_thickness_in")

            print(f"  • Status: COMPLETED in {elapsed}s")
            print(f"  • Overall Verdict: {overall_verdict} (Safety Clearance Blocked: {'✅' if safety_passed else '❌'})")
            print(f"  • Extracted Specs: Concrete PSI={concrete_psi}, Slab Thk={slab_thk} in")

            results.append({
                "condition": deg_id,
                "description": desc,
                "elapsed_seconds": elapsed,
                "overall_verdict": overall_verdict,
                "safety_guardrail_intact": safety_passed,
                "concrete_psi_extracted": concrete_psi,
                "slab_thickness_extracted": slab_thk,
                "passed": safety_passed
            })

        except Exception as e:
            print(f"  • Exception during processing: {str(e)}")
            results.append({
                "condition": deg_id,
                "description": desc,
                "error": str(e),
                "safety_guardrail_intact": False,
                "passed": False
            })

    # Summary report
    report_file = os.path.join(os.path.dirname(__file__), "robustness_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.time(),
            "total_conditions_tested": len(degradations),
            "robustness_results": results
        }, f, indent=2)

    print("\n" + "=" * 80)
    print(f"ROBUSTNESS STRESS TEST COMPLETE! Report saved to: {report_file}")
    print("=" * 80)


if __name__ == "__main__":
    run_robustness_suite()
