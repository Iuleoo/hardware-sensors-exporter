import subprocess
import json
import time
from prometheus_client import start_http_server, Gauge

# ========================
# Prometheus监控指标定义
# ========================
cpu_temp_gauge = Gauge('cpu_temperature', 'Current CPU temperature in Celsius')
nvme_temp_gauge = Gauge('nvme_temperature', 'Current NVMe temperature in Celsius')
network_temp_gauge = Gauge('network_temperature', 'Current network temperature in Celsius')
t5ssd_temp_gauge = Gauge('t5ssd_temperature', 'Samsung T5 SSD temperature in Celsius')

# ========================
# 传感器数据获取函数
# ========================
def get_cpu_temperature():
    try:
        output = subprocess.check_output(["sensors", "-j"]).decode()
        sensors_data = json.loads(output.replace("Â", ""))
        return sensors_data.get('k10temp-pci-00c3', {}).get('Tctl', {}).get('temp1_input')
    except Exception:
        return None

def get_nvme_temperature():
    try:
        output = subprocess.check_output(["sensors", "-j"]).decode()
        sensors_data = json.loads(output.replace("Â", ""))
        return sensors_data.get('nvme-pci-0400', {}).get('Composite', {}).get('temp1_input')
    except Exception:
        return None

def get_network_temperature():
    try:
        output = subprocess.check_output(["sensors", "-j"]).decode()
        sensors_data = json.loads(output.replace("Â", ""))
        return sensors_data.get('mt7921_phy0-pci-0300', {}).get('temp1', {}).get('temp1_input')
    except Exception:
        return None

def get_t5ssd_temperature(device='/dev/sda'):
    """获取T5 SSD温度，支持自动重试机制"""
    retries = 3
    for attempt in range(retries):
        try:
            output = subprocess.check_output(
                ["smartctl", "-a", "-j", device],
                stderr=subprocess.STDOUT
            ).decode()
            smart_data = json.loads(output)
            
            # 双重校验温度数据有效性
            if (temp := smart_data.get('temperature', {}).get('current')) is not None:
                if -40 <= temp <= 150:
                    return temp
            return None
            
        except subprocess.CalledProcessError:
            time.sleep(1)
        except json.JSONDecodeError:
            time.sleep(1)
        except KeyError:
            time.sleep(1)
    return None

# ========================
# 指标收集主函数
# ========================
def collect_metrics():
    if (cpu_temp := get_cpu_temperature()) is not None:
        cpu_temp_gauge.set(cpu_temp)
    
    if (nvme_temp := get_nvme_temperature()) is not None:
        nvme_temp_gauge.set(nvme_temp)
    
    if (network_temp := get_network_temperature()) is not None:
        network_temp_gauge.set(network_temp)
    
    if (ssd_temp := get_t5ssd_temperature()) is not None:
        t5ssd_temp_gauge.set(ssd_temp)
        
# ========================
# 主程序入口
# ========================
if __name__ == "__main__":
    start_http_server(9300)
    
    collect_metrics()
    
    while True:
        try:
            time.sleep(5)
            collect_metrics()
        except KeyboardInterrupt:
            break
        except Exception:
            time.sleep(10)
