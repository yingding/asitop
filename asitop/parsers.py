def parse_thermal_pressure(powermetrics_parse):
    return powermetrics_parse["thermal_pressure"]


def parse_bandwidth_metrics(powermetrics_parse):
    bandwidth_metrics = powermetrics_parse["bandwidth_counters"]
    bandwidth_metrics_dict = {}
    data_fields = ["PCPU0 DCS RD", "PCPU0 DCS WR",
                   "PCPU1 DCS RD", "PCPU1 DCS WR",
                   "PCPU2 DCS RD", "PCPU2 DCS WR",
                   "PCPU3 DCS RD", "PCPU3 DCS WR",
                   "PCPU DCS RD", "PCPU DCS WR",
                   "ECPU0 DCS RD", "ECPU0 DCS WR",
                   "ECPU1 DCS RD", "ECPU1 DCS WR",
                   "ECPU DCS RD", "ECPU DCS WR",
                   "GFX DCS RD", "GFX DCS WR",
                   "ISP DCS RD", "ISP DCS WR",
                   "STRM CODEC DCS RD", "STRM CODEC DCS WR",
                   "PRORES DCS RD", "PRORES DCS WR",
                   "VDEC DCS RD", "VDEC DCS WR",
                   "VENC0 DCS RD", "VENC0 DCS WR",
                   "VENC1 DCS RD", "VENC1 DCS WR",
                   "VENC2 DCS RD", "VENC2 DCS WR",
                   "VENC3 DCS RD", "VENC3 DCS WR",
                   "VENC DCS RD", "VENC DCS WR",
                   "JPG0 DCS RD", "JPG0 DCS WR",
                   "JPG1 DCS RD", "JPG1 DCS WR",
                   "JPG2 DCS RD", "JPG2 DCS WR",
                   "JPG3 DCS RD", "JPG3 DCS WR",
                   "JPG DCS RD", "JPG DCS WR",
                   "DCS RD", "DCS WR"]
    for h in data_fields:
        bandwidth_metrics_dict[h] = 0
    for l in bandwidth_metrics:
        if l["name"] in data_fields:
            bandwidth_metrics_dict[l["name"]] = l["value"]/(1e9)
    bandwidth_metrics_dict["PCPU DCS RD"] = bandwidth_metrics_dict["PCPU DCS RD"] + \
        bandwidth_metrics_dict["PCPU0 DCS RD"] + \
        bandwidth_metrics_dict["PCPU1 DCS RD"] + \
        bandwidth_metrics_dict["PCPU2 DCS RD"] + \
        bandwidth_metrics_dict["PCPU3 DCS RD"]
    bandwidth_metrics_dict["PCPU DCS WR"] = bandwidth_metrics_dict["PCPU DCS WR"] + \
        bandwidth_metrics_dict["PCPU0 DCS WR"] + \
        bandwidth_metrics_dict["PCPU1 DCS WR"] + \
        bandwidth_metrics_dict["PCPU2 DCS WR"] + \
        bandwidth_metrics_dict["PCPU3 DCS WR"]
    bandwidth_metrics_dict["JPG DCS RD"] = bandwidth_metrics_dict["JPG DCS RD"] + \
        bandwidth_metrics_dict["JPG0 DCS RD"] + \
        bandwidth_metrics_dict["JPG1 DCS RD"] + \
        bandwidth_metrics_dict["JPG2 DCS RD"] + \
        bandwidth_metrics_dict["JPG3 DCS RD"]
    bandwidth_metrics_dict["JPG DCS WR"] = bandwidth_metrics_dict["JPG DCS WR"] + \
        bandwidth_metrics_dict["JPG0 DCS WR"] + \
        bandwidth_metrics_dict["JPG1 DCS WR"] + \
        bandwidth_metrics_dict["JPG2 DCS WR"] + \
        bandwidth_metrics_dict["JPG3 DCS WR"]
    bandwidth_metrics_dict["VENC DCS RD"] = bandwidth_metrics_dict["VENC DCS RD"] + \
        bandwidth_metrics_dict["VENC0 DCS RD"] + \
        bandwidth_metrics_dict["VENC1 DCS RD"] + \
        bandwidth_metrics_dict["VENC2 DCS RD"] + \
        bandwidth_metrics_dict["VENC3 DCS RD"]
    bandwidth_metrics_dict["VENC DCS WR"] = bandwidth_metrics_dict["VENC DCS WR"] + \
        bandwidth_metrics_dict["VENC0 DCS WR"] + \
        bandwidth_metrics_dict["VENC1 DCS WR"] + \
        bandwidth_metrics_dict["VENC2 DCS WR"] + \
        bandwidth_metrics_dict["VENC3 DCS WR"]
    bandwidth_metrics_dict["MEDIA DCS"] = sum([
        bandwidth_metrics_dict["ISP DCS RD"], bandwidth_metrics_dict["ISP DCS WR"],
        bandwidth_metrics_dict["STRM CODEC DCS RD"], bandwidth_metrics_dict["STRM CODEC DCS WR"],
        bandwidth_metrics_dict["PRORES DCS RD"], bandwidth_metrics_dict["PRORES DCS WR"],
        bandwidth_metrics_dict["VDEC DCS RD"], bandwidth_metrics_dict["VDEC DCS WR"],
        bandwidth_metrics_dict["VENC DCS RD"], bandwidth_metrics_dict["VENC DCS WR"],
        bandwidth_metrics_dict["JPG DCS RD"], bandwidth_metrics_dict["JPG DCS WR"],
    ])
    return bandwidth_metrics_dict


def cluster_prefix(name):
    return name.split("-")[0].rstrip("0123456789")


def cluster_tier(prefix, cpu_count, e_core_count, p_core_count):
    # "E" is the lower tier (hw.perflevel1), "P" the higher one (hw.perflevel0).
    if e_core_count != p_core_count:
        if cpu_count == e_core_count:
            return "E"
        if cpu_count == p_core_count:
            return "P"
    return "E" if prefix == "E" else "P"


def active_ratio(sample):
    idle = sample.get("idle_ratio", 1.0)
    return 1 - min(max(idle, 0.0), 1.0)


def freq_mhz(sample):
    return int(sample.get("freq_hz", 0)/(1e6))


def parse_cpu_metrics(powermetrics_parse, e_core_count=None, p_core_count=None):
    cpu_metrics = powermetrics_parse["processor"]
    cpu_metric_dict = {}
    # cpu_clusters
    groups = {}
    for cluster in cpu_metrics.get("clusters", []):
        name = cluster["name"]
        cpu_metric_dict[name+"_freq_Mhz"] = freq_mhz(cluster)
        cpu_metric_dict[name+"_active"] = int(active_ratio(cluster)*100)
        groups.setdefault(cluster_prefix(name), []).append(cluster)
    tiers = {"E": [], "P": []}
    for prefix, clusters in groups.items():
        cpu_count = sum(len(c.get("cpus") or []) for c in clusters)
        tiers[cluster_tier(prefix, cpu_count, e_core_count, p_core_count)].extend(clusters)
    for tier, clusters in tiers.items():
        name = tier + "-Cluster"
        cores = []
        busy = 0.0
        weight = 0
        busy_freq = 0.0
        max_freq = 0
        for cluster in clusters:
            cpus = cluster.get("cpus") or []
            for sample in cpus or [cluster]:
                active = active_ratio(sample)
                freq = freq_mhz(sample)
                busy += active
                weight += 1
                busy_freq += freq * active
                max_freq = max(max_freq, freq)
                if sample is not cluster and "cpu" in sample:
                    key = name + str(sample["cpu"])
                    cores.append(sample["cpu"])
                    cpu_metric_dict[key + "_freq_Mhz"] = freq
                    cpu_metric_dict[key + "_active"] = int(active * 100)
        cpu_metric_dict[tier.lower() + "_core"] = cores
        cpu_metric_dict[name + "_active"] = int(busy / weight * 100) if weight else 0
        cpu_metric_dict[name + "_freq_Mhz"] = round(busy_freq / busy) if busy > 0 else max_freq
    # power
    cpu_metric_dict["ane_W"] = cpu_metrics.get("ane_energy", 0)/1000
    #cpu_metric_dict["dram_W"] = cpu_metrics["dram_energy"]/1000
    cpu_metric_dict["cpu_W"] = cpu_metrics.get("cpu_energy", 0)/1000
    cpu_metric_dict["gpu_W"] = cpu_metrics.get("gpu_energy", 0)/1000
    cpu_metric_dict["package_W"] = cpu_metrics.get("combined_power", 0)/1000
    return cpu_metric_dict


def parse_gpu_metrics(powermetrics_parse):
    gpu_metrics = powermetrics_parse.get("gpu") or {}
    gpu_metrics_dict = {
        "freq_MHz": int(gpu_metrics.get("freq_hz", 0)),
        "active": int(active_ratio(gpu_metrics)*100),
    }
    return gpu_metrics_dict
