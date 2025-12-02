import subprocess
import sys


def run():
    # 第一阶段：生成假数据
    print("🔧 Step 1: Reset + seed mock data (setup-demo)")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "student_wellbeing_monitor.tools.setup_demo",
            "--with-mock",
        ]
    )
    if result.returncode != 0:
        print("❌ setup-demo failed.")
        sys.exit(result.returncode)

    print("✅ Mock data generated successfully!\n")

    # 第二阶段：启动 Web
    print("🌐 Step 2: Starting wellbeing dashboard ...")
    subprocess.run([sys.executable, "-m", "student_wellbeing_monitor.ui.app"])
