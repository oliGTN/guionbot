let redeployMode = false;
let totalFillable = 0;
let withFights = true;

function getCharacters(str) {
  const parts = [...str]
  return parts
}

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

        processNextStep();
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
        const stars_text = svg.parentNode.querySelector('.stars');

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

        const graph = {
            svg,
            stars_text,
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
        };
        deployGraphs.push(graph);

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

function updateTotalStars() {
    const yellow_star = "⭐";

    let additional_stars = 0;
    deployGraphs.forEach(graph => {
        const currentStars_txt = graph.stars_text.textContent.trim();
        if (currentStars_txt.includes('>')) {
            const originalStars_txt = currentStars_txt.split(">")[0].trim();
            const newStars_txt = currentStars_txt.split(">")[1].trim();

            const originalStars_count = (originalStars_txt.length - originalStars_txt.replaceAll(yellow_star, "").length) / yellow_star.length;
            const newStars_count = (newStars_txt.length - newStars_txt.replaceAll(yellow_star, "").length) / yellow_star.length;

            additional_stars += (newStars_count-originalStars_count);
        }
    });

    // Update total star count for the phase
    total_stars_div = document.getElementById('total-stars');
    total_stars_txt = total_stars_div.textContent;
    total_stars_count = parseNumber(total_stars_txt.split(yellow_star)[0]);

    total_stars_div.textContent = total_stars_count.toString()+yellow_star
    if (additional_stars >0 ) {
        total_stars_div.textContent += " > "+(total_stars_count+additional_stars).toString()+yellow_star;
    }


}

function updateStars(graph) {
    const blue_circle = "🔵";
    const gray_circle = "●";
    const yellow_star = "⭐";
    const gray_star = "★";

    const currentStars_txt = graph.stars_text.textContent.trim();

    // Detect if this is a "3 stars" zone or a "2 boxes and 1 star" zone
    const currentStars_firstChar = getCharacters(currentStars_txt)[0];
    let star_zone = true;
    if (currentStars_firstChar==blue_circle || currentStars_firstChar==gray_circle) {
        // box zone
        star_zone = false;
    }

    // Detect amount of final stars, after estimated fights+deployments
    let newStars_txt = "";
    let  additional_stars = 0;
    const currentValue = Math.min(graph.currentValue, graph.finalValue);
    if (currentValue > graph.steps[0]) {
        if (star_zone) {
            newStars_txt += yellow_star;
            if (currentValue-graph.currentDeploy <= graph.steps[0]) {
                additional_stars += 1;
            }
        } else {
            newStars_txt += blue_circle;
        }
    } else {
        if (star_zone) {
            newStars_txt += gray_star;
        } else {
            newStars_txt += gray_circle;
        }
    }

    if (currentValue >= graph.steps[1]) {
        if (star_zone) {
            newStars_txt += yellow_star;
            if (currentValue-graph.currentDeploy < graph.steps[1]) {
                additional_stars += 1;
            }
        } else {
            newStars_txt += blue_circle;
        }
    } else {
        if (star_zone) {
            newStars_txt += gray_star;
        } else {
            newStars_txt += gray_circle;
        }
    }

    if (currentValue >= graph.finalValue) {
        newStars_txt += yellow_star;
        if (currentValue-graph.currentDeploy < graph.finalValue) {
            additional_stars += 1;
        }
    } else {
        newStars_txt += gray_star;
    }

    // Write star text
    const originalStars_txt = currentStars_txt.split(">")[0].trim();

    if (originalStars_txt != newStars_txt) {
        completeStars_txt = originalStars_txt + " > " + newStars_txt;
        graph.stars_text.textContent = completeStars_txt;
    } else {
        graph.stars_text.textContent = originalStars_txt;
    }

    updateTotalStars();
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
    updateStars(graph);
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

        updateStars(graph);
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
    autoRedeploy();

    const btn_redeploy = document.getElementById('btn_redeploy');
    if (btn_redeploy) btn_redeploy.addEventListener('click', startRedeploy);
    const btn_auto = document.getElementById('btn_auto');
    if (btn_auto) btn_auto.addEventListener('click', autoRedeploy);
    const with_fights = document.getElementById('with_fights');
    if (with_fights) with_fights.addEventListener('change', function() {
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
