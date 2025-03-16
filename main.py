import subprocess
import json
import time
from prometheus_client import start_http_server, Gauge

# ========================
# Prometheus指标注册
# ========================
METRICS = {
    'cpu_temperature': Gauge('cpu_temperature', 'CPU温度 (Tctl)', ['chip']),
    'nvme_temperature': Gauge('nvme_temperature', 'NVMe复合温度', ['device']),
    'network_temperature': Gauge('network_temperature', '无线网卡温度', ['interface']),
    'ssd_temperature': Gauge('ssd_temperature', '外置SSD温度', ['model'])
}

# ========================
# 传感器数据统一获取
# ========================
def get_sensor_data():
    try:
        output = subprocess.check_output(["sensors", "-j"], timeout=3).decode()
        return json.loads(output.replace("Â", ""))
    except Exception as e:
        METRICS['cpu_temperature'].labels('k10temp').set(-1)  # 错误状态标记
        return None

# ========================
# 温度解析专用方法
# ========================
def parse_temperature(data, path):
    """通用温度解析方法，路径格式：chip.key1.key2"""
    keys = path.split('.')
    value = data
    for key in keys:
        value = value.get(key, {})
    return float(value) if isinstance(value, (int, float)) else None

# ========================
# SSD温度监控专用方法
# ========================
def get_ssd_temp(device='/dev/sda'):
    try:
        output = subprocess.check_output(
            ["sudo", "smartctl", "-j", "-A", device],
            timeout=5, stderr=subprocess.DEVNULL
        )
        data = json.loads(output)
        return data.get('temperature', {}).get('current')
    except:
        return None

# ========================
# 指标收集主逻辑
# ========================
def collect():
    sensor_data = get_sensor_data()
    
    # CPU温度（AMD Tctl）
    if sensor_data:
        cpu_temp = parse_temperature(sensor_data, 'k10temp-pci-00c3.Tctl.temp1_input')
        METRICS['cpu_temperature'].labels('k10temp').set(cpu_temp or 0)
        
        # NVMe复合温度
        nvme_temp = parse_temperature(sensor_data, 'nvme-pci-0400.Composite.temp1_input') 
        METRICS['nvme_temperature'].labels('nvme0').set(nvme_temp or 0)
        
        # 无线网卡温度
        wifi_temp = parse_temperature(sensor_data, 'mt7921_phy0-pci-0300.temp1.temp1_input')
        METRICS['network_temperature'].labels('wlan0').set(wifi_temp or 0)
    
    # 外置SSD温度
    if (ssd_temp := get_ssd_temp()) is not None:
        METRICS['ssd_temperature'].labels('Samsung_T5').set(ssd_temp)

# ========================
# 服务启动
# ========================
if __name__ == "__main__":
    start_http_server(9300)
    while True:
        collect()
        time.sleep(5)
