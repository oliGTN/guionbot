let redeployMode = false;
let totalFillable = 0;
let withFights = true;

function autoRedeploy() {
    startRedeploy();

    function processNextStep() {
        if (totalFillable <= 0) {
            return;
        }

        // Find all deployable graphs
        const candidates = [];

        deployGraphs.forEach(graph => {
            const target = getNextTarget(graph);

            if (!target) {
                return;
            }

            const needed = target - graph.currentValue;

            if (needed > 0) {
                candidates.push({
                    graph,
                    needed,
                    target
                });
            }
        });

        if (candidates.length === 0) {
            return;
        }

        // Choose graph closest to next step
        candidates.sort((a, b) => a.needed - b.needed);

        const selected = candidates[0];

        fillGraph(selected.graph);

        // Continue automatically
        setTimeout(processNextStep, 300);
    }

    processNextStep();

    // remove the focus from the button when done
    document.activeElement.blur();
}

function parseNumber(str) {
    return parseInt(str.replace(/[^0-9]/g, ''), 10) || 0;
}

function formatNumber(num) {
    return num.toLocaleString('fr-FR');
}

// Store all graph data
const deployGraphs = [];

function initRedeployGraphs() {
    const deployRects = document.querySelectorAll('rect[id^="deploy-"]');

    deployRects.forEach(rect => {
        const svg = rect.closest('svg');

        const orangeRect = svg.querySelector('rect[id^="fights-"]');
        const greenRect = svg.querySelector('rect[style*="fill:green"]');

        const texts = svg.querySelectorAll('text');

        // Last text = final value
        const finalValue = parseNumber(texts[texts.length - 2].textContent);

        // Step values = all bottom labels except 0 and final
        const steps = [];

        for (let i = 1; i < texts.length - 2; i++) {
            const val = parseNumber(texts[i].textContent);

            if (val > 0 && val < finalValue) {
                steps.push(val);
            }
        }

        // Current value from green bar title
        const currentTitle = greenRect.querySelector('title').textContent;
        const currentValue = parseNumber(currentTitle);

        const orangeTitle = orangeRect.querySelector('title').textContent;
        const orangeValue = parseNumber(orangeTitle);

        const baseValueWithFights = currentValue + orangeValue;
        const baseValueWithoutFights = currentValue;

        deployGraphs.push({
            svg,
            deployRect: rect,
            orangeRect,
            greenRect,
            steps,
            finalValue,
            baseValueWithFights,
            baseValueWithoutFights,
            currentValue: baseValueWithFights,
            currentDeploy: 0,
            originalOrangeWidth: orangeRect.getAttribute('width'),
            originalOrangeX: orangeRect.getAttribute('x')
        });

        svg.style.cursor = 'pointer';
    });
}

function updateRemainingDisplay() {
    const labels = document.querySelectorAll('.stat-detail label');

    labels.forEach(label => {
        if (label.textContent.trim() === 'Remaining deployments') {
            const valueElement = label.parentElement.querySelector('value');
            valueElement.textContent = formatNumber(totalFillable);
        }
    });
}

function updateDeployBar(graph) {
    const totalBarValue = graph.finalValue;

    const yellowPercent = (graph.currentDeploy / totalBarValue) * 100;
    const orangePercent = parseFloat(graph.orangeRect.getAttribute('width'));
    const greenPercent = parseFloat(graph.greenRect.getAttribute('width'));

    graph.deployRect.setAttribute('x', (greenPercent + orangePercent) + '%');
    graph.deployRect.setAttribute('width', yellowPercent + '%');

    const title = graph.deployRect.querySelector('title');
    title.textContent = 'Deployments: ' + formatNumber(graph.currentDeploy);
}

function getNextTarget(graph) {
    for (const step of graph.steps) {
        if (graph.currentValue < step) {
            return step;
        }
    }

    if (graph.currentValue < graph.finalValue) {
        return graph.finalValue;
    }

    return null;
}

function fillGraph(graph) {
    if (!redeployMode || totalFillable <= 0) {
        return;
    }

    const target = getNextTarget(graph);

    if (!target) {
        return;
    }

    const needed = target - graph.currentValue;
    const fillAmount = Math.min(needed, totalFillable);

    if (fillAmount <= 0) {
        return;
    }

    graph.currentDeploy += fillAmount;
    graph.currentValue += fillAmount;

    totalFillable -= fillAmount;

    updateDeployBar(graph);
    //updateRemainingDisplay();
}

function applyFightMode() {
    deployGraphs.forEach(graph => {
        // Reset yellow
        graph.currentDeploy = 0;
        graph.deployRect.setAttribute('width', '0%');

        const deployTitle = graph.deployRect.querySelector('title');
        deployTitle.textContent = 'Deployments: 0';

        if (withFights) {
            // Restore orange
            graph.orangeRect.setAttribute('width', graph.originalOrangeWidth);
            graph.orangeRect.setAttribute('x', graph.originalOrangeX);

            graph.currentValue = graph.baseValueWithFights;

            const greenPercent = parseFloat(graph.greenRect.getAttribute('width'));
            const orangePercent = parseFloat(graph.originalOrangeWidth);

            graph.deployRect.setAttribute('x', (greenPercent + orangePercent) + '%');
        }
        else {
            // Remove orange
            graph.orangeRect.setAttribute('width', '0%');

            const greenPercent = parseFloat(graph.greenRect.getAttribute('width'));

            graph.deployRect.setAttribute('x', greenPercent + '%');

            graph.currentValue = graph.baseValueWithoutFights;
        }
    });
}

function startRedeploy() {
    redeployMode = true;

    // Read remaining deployments value
    const labels = document.querySelectorAll('.stat-detail label');

    labels.forEach(label => {
        if (label.textContent.trim() === 'Remaining deployments') {
            const valueElement = label.parentElement.querySelector('value');
            totalFillable = parseNumber(valueElement.textContent);
        }
    });

    applyFightMode();

    //updateRemainingDisplay();
}

// Initialize when page is ready
window.addEventListener('DOMContentLoaded', () => {
    initRedeployGraphs();

    document.getElementById('btn_redeploy').addEventListener('click', startRedeploy);
    document.getElementById('btn_auto').addEventListener('click', autoRedeploy);
    document.getElementById('with_fights').addEventListener('change', function() {
        withFights = this.checked;

        applyFightMode();
    });
    // Add click handlers to graphs
    deployGraphs.forEach(graph => {
        graph.svg.addEventListener('click', () => {
            fillGraph(graph);
        });
    });
});
