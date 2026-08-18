import subprocess
import sys

files = [
    "EHR_Deny_Oxygen.pdf",
    "EHR_NurseReview_Oxygen.pdf",
    "EHR_Pending_Oxygen.pdf"
]

for f in files:
    print(f"\n======================================")
    print(f"Testing {f}")
    print(f"======================================")
    # create a temporary script
    script = f"""from test_pipeline import run_test\nrun_test(r'e:\\synthea_sample_data_ccda_latest\\cms-prior-auth\\backend\\{f}')\n"""
    with open("temp_run.py", "w") as tf:
        tf.write(script)
    
    result = subprocess.run([sys.executable, "temp_run.py"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("ERROR:", result.stderr)
