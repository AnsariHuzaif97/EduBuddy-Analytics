let currentAnalysis = null;
let baseInputData = {};
let debounceTimer;

// Initialize everything on load
document.addEventListener('DOMContentLoaded', () => {
    // Load Onboarding Data
    const obData = localStorage.getItem('eduBuddyOnboarding');
    if (obData) {
        try {
            const data = JSON.parse(obData);
            
            const setVal = (id, val) => { 
                if(val !== undefined && val !== null) {
                    const el = document.getElementById(id);
                    if(el) el.value = val;
                }
            };
            const setRadio = (name, val) => {
                if(val !== undefined && val !== null) {
                    const radios = document.getElementsByName(name);
                    for(let r of radios) { if(r.value === val) r.checked = true; }
                }
            };
            const setRange = (id, val, textId) => {
                if(val !== undefined && val !== null) {
                    const el = document.getElementById(id);
                    const txt = document.getElementById(textId);
                    if(el) el.value = val;
                    if(txt) txt.innerText = val;
                }
            };

            setVal('code_module', data.code_module);
            setVal('code_presentation', data.code_presentation);
            setVal('highest_education', data.highest_education);
            setVal('region', data.region);
            setVal('imd_band', data.imd_band);
            
            setRadio('gender', data.gender);
            setRadio('age', data.age_band);
            setRadio('disability', data.disability);
            
            setRange('studied_credits', data.studied_credits, 'credits-val');
            setRange('total_clicks', data.total_clicks, 'clicks-val');
            setRange('active_days', data.active_days, 'days-val');
            setRange('activity_span', data.activity_span, 'span-val');
            setRange('avg_assignment_score', data.avg_assignment_score, 'scores-val');
        } catch(e) {
            console.error("Error parsing onboarding data", e);
        }
    }

    // Setup event listeners for all inputs
    const inputs = document.querySelectorAll('input, select');
    inputs.forEach(input => {
        input.addEventListener('change', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(fetchData, 300);
        });
        if(input.type === 'range') {
            input.addEventListener('input', () => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(fetchData, 300);
            });
        }
    });
    
    // Initial fetch
    fetchData();
});

function handleLogout(event) {
    if(event) event.preventDefault();
    // Do not remove localStorage so data is remembered for next login
    window.location.href = 'index.html';
}

// UI Helpers
function toggleCollapsible(id) {
    const content = document.getElementById(id);
    content.classList.toggle('open');
}

function switchTab(evt, tabId) {
    // Hide all contents
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    // Remove active from all tabs
    document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
    
    // Show selected
    document.getElementById(tabId).classList.add('active');
    evt.currentTarget.classList.add('active');
    
    if(tabId === 'telemetry') {
        fetchTelemetry();
    }
}

function updateSimDisplay(id, val) {
    document.getElementById(id).innerText = val;
}

// API Integration
function gatherInputs() {
    const getVal = id => document.getElementById(id).value;
    const getRadio = name => document.querySelector(`input[name="${name}"]:checked`).value;
    
    const active_days = parseInt(getVal('active_days'));
    const total_clicks = parseInt(getVal('total_clicks'));
    const avg_clicks_per_day = active_days > 0 ? (total_clicks / active_days) : 0;
    
    return {
        code_module: getVal('code_module'),
        code_presentation: getVal('code_presentation'),
        highest_education: getVal('highest_education'),
        studied_credits: parseInt(getVal('studied_credits')),
        gender: getRadio('gender'),
        region: getVal('region'),
        imd_band: getVal('imd_band'),
        age_band: getRadio('age'),
        disability: getRadio('disability'),
        total_clicks: total_clicks,
        active_days: active_days,
        activity_span: parseInt(getVal('activity_span')),
        avg_assignment_score: parseFloat(getVal('avg_assignment_score')),
        module_presentation_length: 268,
        num_of_prev_attempts: 0,
        avg_clicks_per_day: avg_clicks_per_day
    };
}

async function fetchData() {
    baseInputData = gatherInputs();
    
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(baseInputData)
        });
        if (!response.ok) throw new Error('API Error');
        
        const res = await response.json();
        currentAnalysis = res;
        updateDashboard(res);
        triggerSimulation(); // Update simulation lab as well
        
    } catch (error) {
        console.error('Failed to fetch data:', error);
    }
}

async function fetchTelemetry() {
    const imgEl = document.getElementById('telemetry-plot');
    const loader = document.getElementById('telemetry-loader');
    
    imgEl.style.display = 'none';
    loader.style.display = 'block';
    
    try {
        const response = await fetch('/api/telemetry', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(baseInputData)
        });
        if (!response.ok) throw new Error('Telemetry Error');
        
        const res = await response.json();
        imgEl.src = res.image;
        imgEl.style.display = 'block';
        loader.style.display = 'none';
    } catch (error) {
        console.error('Failed to fetch telemetry:', error);
        loader.style.display = 'none';
    }
}

// UI Updates
function updateDashboard(res) {
    const prob = res.success_probability;
    const isRisky = res.prediction === "AT RISK";
    
    // Gauge Chart Update
    renderGauge(prob, isRisky);
    
    // Update Card Styles
    const card = document.getElementById('outlook-card');
    const label = document.getElementById('outlook-label');
    if(isRisky) {
        card.className = 'premium-card neon-border-rose';
        label.style.color = 'var(--accent-rose)';
    } else {
        card.className = 'premium-card neon-border-emerald';
        label.style.color = 'var(--accent-emerald)';
    }
    
    // Habitual Convergence Updates
    const curr = res.current_behavior;
    const targ = res.target_behavior;
    
    updateMetric('m-focus', 'd-focus', curr.active_days, curr.active_days - targ.active_days);
    updateMetric('m-lms', 'd-lms', curr.total_clicks, curr.total_clicks - targ.total_clicks);
    updateMetric('m-mastery', 'd-mastery', curr.avg_assignment_score.toFixed(1) + '%', (curr.avg_assignment_score - targ.avg_assignment_score).toFixed(1));
    
    // Roadmap Timeline Updates
    document.getElementById('roadmap-weeks').innerText = `${res.remaining_weeks} Production Weeks`;
    
    const plan = res.weekly_plan;
    const needs = res.improvement_needed;
    const timelineContainer = document.getElementById('timeline-container');
    
    let daysText = plan.days_per_week ? plan.days_per_week : 'Optimal';
    let clicksText = plan.clicks_per_week ? plan.clicks_per_week : 'Optimal';
    let deltaText = needs.marks_improvement > 0 
        ? `Bridge your grade gap by <b>+${needs.marks_improvement} marks</b>.` 
        : "Academic metrics have reached baseline success targets.";
        
    timelineContainer.innerHTML = `
        <div class="timeline-node">
            <p class="timeline-title">Engagement Target</p>
            <p class="timeline-desc">Maintain consistent LMS interactions between <b>${daysText}</b> study days weekly.</p>
        </div>
        <div class="timeline-node">
            <p class="timeline-title">Behavioral Intensity</p>
            <p class="timeline-desc">Sustain/Target <b>${clicksText}</b> platform clicks per session cycle.</p>
        </div>
        <div class="timeline-node">
            <p class="timeline-title">Academic Delta</p>
            <p class="timeline-desc">${deltaText}</p>
        </div>
    `;
}

function updateMetric(valId, deltaId, val, delta) {
    document.getElementById(valId).innerText = val;
    const dEl = document.getElementById(deltaId);
    let dVal = parseFloat(delta);
    if (dVal > 0) {
        dEl.innerText = `+${delta}`;
        dEl.className = 'metric-delta delta-positive';
    } else if (dVal < 0) {
        dEl.innerText = delta;
        dEl.className = 'metric-delta delta-negative';
    } else {
        dEl.innerText = '0';
        dEl.className = 'metric-delta';
        dEl.style.color = 'var(--text-secondary)';
    }
}

function renderGauge(probability, isRisky) {
    const color = isRisky ? "#f43f5e" : "#10b981";
    const data = [
        {
            type: "indicator",
            mode: "gauge+number",
            value: probability * 100,
            domain: { x: [0, 1], y: [0, 1] },
            number: { font: { size: 60, color: "#f8fafc", family: "Outfit" }, suffix: "%" },
            gauge: {
                axis: { range: [0, 100], tickwidth: 1, tickcolor: "rgba(255,255,255,0.1)" },
                bar: { color: color },
                bgcolor: "rgba(255,255,255,0.03)",
                borderwidth: 0,
                steps: [
                    { range: [0, 50], color: "rgba(244, 63, 94, 0.1)" },
                    { range: [50, 100], color: "rgba(16, 185, 129, 0.1)" }
                ],
                threshold: {
                    line: { color: color, width: 4 },
                    thickness: 0.75,
                    value: probability * 100
                }
            }
        }
    ];

    const layout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: "#94a3b8", family: "Inter" },
        margin: { l: 20, r: 20, t: 30, b: 20 },
        height: 300
    };

    Plotly.newPlot('gauge-container', data, layout, {displayModeBar: false, responsive: true});
}

async function triggerSimulation() {
    if(!currentAnalysis) return;
    
    const sh_days = parseInt(document.getElementById('sh_days').value);
    const sh_clicks = parseInt(document.getElementById('sh_clicks').value);
    const sh_scores = parseFloat(document.getElementById('sh_scores').value);
    
    let simInput = { ...baseInputData };
    simInput.active_days += sh_days;
    simInput.total_clicks += sh_clicks;
    simInput.avg_assignment_score = Math.min(100.0, simInput.avg_assignment_score + sh_scores);
    if (simInput.active_days > 0) {
        simInput.avg_clicks_per_day = simInput.total_clicks / simInput.active_days;
    }

    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(simInput)
        });
        if (!response.ok) return;
        const res = await response.json();
        
        const simProb = res.success_probability;
        const baseProb = currentAnalysis.success_probability;
        const diff = simProb - baseProb;
        
        document.getElementById('sim-prediction').innerText = (simProb * 100).toFixed(1) + '%';
        
        const impactEl = document.getElementById('sim-impact');
        if (diff > 0) {
            impactEl.innerText = `+${(diff * 100).toFixed(1)}%`;
            impactEl.style.color = 'var(--accent-emerald)';
        } else {
            impactEl.innerText = `${(diff * 100).toFixed(1)}%`;
            impactEl.style.color = 'var(--accent-rose)';
        }
        
    } catch(e) {
        console.error(e);
    }
}

function downloadReport() {
    if(!currentAnalysis) return;
    
    const res = currentAnalysis;
    const plan = JSON.stringify(res.weekly_plan);
    const text = `EDUCATIONAL SUCCESS REPORT\n${res.remaining_weeks} Weeks Remaining\nTargets: ${plan}`;
    
    const blob = new Blob([text], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'strategy_report.txt';
    a.click();
    URL.revokeObjectURL(a.href);
}
