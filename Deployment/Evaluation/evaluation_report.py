python3 - << 'EOF'
import json, sqlite3, statistics
from collections import Counter

DB = "/opt/energy-profiller-hiran/deployments.db"
DECISIONS = "/opt/energy-profiller-hiran/agent_decisions.json"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

print("="*60)
print("STRATEGY SUMMARY")
print("="*60)
rows = conn.execute("""
    SELECT d.strategy,
           COUNT(*) as count,
           ROUND(AVG(cr.total_g_co2),4) as avg_co2_g,
           ROUND(MIN(cr.total_g_co2),4) as min_co2_g,
           ROUND(MAX(cr.total_g_co2),4) as max_co2_g,
           ROUND(AVG(d.duration_minutes),3) as avg_duration_min,
           ROUND(AVG(cr.total_energy_kwh),6) as avg_energy_kwh,
           ROUND(AVG(cr.infra_multiplier),2) as avg_infra_mult
    FROM deployments d
    JOIN carbon_reports cr ON d.id = cr.deployment_id
    WHERE cr.total_g_co2 IS NOT NULL AND d.strategy IS NOT NULL
    GROUP BY d.strategy
    ORDER BY avg_co2_g ASC
""").fetchall()
for r in rows:
    print(dict(r))

print("\n" + "="*60)
print("CARBON SNAPSHOTS")
print("="*60)
rows = conn.execute("""
    SELECT strategy, phase, COUNT(*) as count,
           ROUND(AVG(infra_multiplier),2) as avg_infra,
           ROUND(AVG(downtime_seconds),1) as avg_downtime
    FROM carbon_snapshots
    GROUP BY strategy, phase
    ORDER BY strategy, phase
""").fetchall()
for r in rows:
    print(dict(r))

print("\n" + "="*60)
print("ALL CARBON REPORT ROWS")
print("="*60)
rows = conn.execute("""
    SELECT d.strategy, cr.total_g_co2, cr.total_energy_kwh,
           cr.carbon_intensity_gco2, cr.infra_multiplier, d.duration_minutes
    FROM carbon_reports cr
    JOIN deployments d ON cr.deployment_id = d.id
    WHERE cr.total_g_co2 IS NOT NULL
    ORDER BY d.strategy
""").fetchall()
for r in rows:
    print(dict(r))

print("\n" + "="*60)
print("AGENT DECISIONS ANALYSIS")
print("="*60)
with open(DECISIONS) as f:
    decisions = json.load(f)

scores = [d['green_score'] for d in decisions if isinstance(d.get('green_score'), (int,float))]
deploy_count = sum(1 for d in decisions if d.get('decision')=='deploy')
wait_count   = sum(1 for d in decisions if d.get('decision')=='wait')
strategies   = Counter(d.get('strategy') for d in decisions if d.get('decision')=='deploy')
grades       = Counter(d.get('green_grade') for d in decisions if d.get('green_grade') and d.get('green_grade')!='N/A')
carbon_ratings = Counter(d.get('carbon_rating') for d in decisions)
methods      = Counter(d.get('method','llm_react') for d in decisions)

print(f"Total: {len(decisions)} | Deploy: {deploy_count} | Wait: {wait_count}")
print(f"Strategy breakdown: {dict(strategies)}")
print(f"Grade distribution: {dict(grades)}")
print(f"Carbon ratings: {dict(carbon_ratings)}")
print(f"Methods: {dict(methods)}")

if scores:
    print(f"Scores: mean={round(statistics.mean(scores),1)} stdev={round(statistics.stdev(scores),1) if len(scores)>1 else 'N/A'} min={min(scores)} max={max(scores)}")

score_fields = ['carbon','cpu','memory','business_time','history','timing']
print("Avg score breakdown:")
for field in score_fields:
    vals = [d['score_breakdown'][field] for d in decisions
            if d.get('score_breakdown') and field in d.get('score_breakdown',{})]
    if vals:
        print(f"  {field}: {round(statistics.mean(vals),1)}")

print("\nWait decisions:")
for d in decisions:
    if d.get('decision') == 'wait':
        print(f"  carbon={d.get('carbon_intensity_gco2_kwh')} score={d.get('green_score')} window={d.get('next_green_window')}")

deploy_i = [d.get('carbon_intensity_gco2_kwh') for d in decisions
            if d.get('decision')=='deploy' and d.get('carbon_intensity_gco2_kwh')]
wait_i   = [d.get('carbon_intensity_gco2_kwh') for d in decisions
            if d.get('decision')=='wait' and d.get('carbon_intensity_gco2_kwh')]
if deploy_i:
    print(f"\nCarbon at DEPLOY: mean={round(statistics.mean(deploy_i),1)} min={min(deploy_i)} max={max(deploy_i)}")
if wait_i:
    print(f"Carbon at WAIT:   mean={round(statistics.mean(wait_i),1)} min={min(wait_i)} max={max(wait_i)}")

conn.close()
EOF