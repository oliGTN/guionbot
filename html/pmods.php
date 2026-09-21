<?php
require_once 'security.php';

ini_set('session.gc_maxlifetime', 3600 * 24 * 7);
session_set_cookie_params([
    'lifetime' => 3600 * 24 * 7,
    'path' => '/',
    'secure' => true,
    'httponly' => true,
    'samesite' => 'Lax',
]);
session_start();

require 'guionbotdb.php';
include 'pvariables.php';

$isAdmin = !empty($_SESSION['admin']);

if (!isset($_GET['ac'])) {
    header('Location: index.php');
    exit();
}

$allycode = get_required_ally_code();
[$isMyAllycode, $isMyAllycodeConfirmed, $isGuildMate, $isGuildMateConfirmed] = set_session_rights_for_allycode($allycode);

include 'pdata.php';

try {
    $stmt = $conn_guionbot->prepare(
        "SELECT slot, mod_set, pips, mods.level, tier, roster.defId
         FROM mods
         JOIN roster ON roster.id = mods.roster_id
         WHERE allyCode = :allycode
         ORDER BY slot, mod_set"
    );
    $stmt->execute([':allycode' => $allycode]);
    $mods = $stmt->fetchAll(PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    error_log('Error fetching player mods: ' . $e->getMessage());
    $mods = [];
}

$slot_names = [
    2 => 'square',
    3 => 'arrow',
    4 => 'diamond',
    5 => 'triangle',
    6 => 'circle',
    7 => 'cross',
];

$set_names = [
    1 => 'health',
    2 => 'offense',
    3 => 'defense',
    4 => 'speed',
    5 => 'critchance',
    6 => 'critdamage',
    7 => 'potency',
    8 => 'tenacity',
];

// Keep the character filter list limited to characters that actually have a mod.
$character_ids = [];
foreach ($mods as $mod) {
    if (!empty($mod['defId'])) {
        $character_ids[$mod['defId']] = true;
    }
}
$character_ids = array_keys($character_ids);
sort($character_ids, SORT_NATURAL | SORT_FLAG_CASE);
?>
<!DOCTYPE html>
<html>
<head>
    <title>GuiOn bot for SWGOH</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="basic.css">
    <link rel="stylesheet" href="tables.css">
    <link rel="stylesheet" href="navbar.css">
    <link rel="stylesheet" href="main.1.008.css">
    <link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">
    <style>
        .mod-filter {
            margin-bottom: 1.25rem;
            padding: 1rem;
        }

        .mod-filter-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            cursor: pointer;
        }

        .mod-filter-header h4 {
            margin: 0;
        }

        .mod-filter-summary {
            font-size: 0.9rem;
            opacity: 0.8;
            margin-top: 0.25rem;
        }

        .mod-filter-body {
            margin-top: 1rem;
        }

        .filter-condition {
            display: grid;
            grid-template-columns: 90px 90px minmax(140px, 1fr) 90px;
            gap: 0.5rem;
            align-items: center;
            margin-bottom: 0.5rem;
        }

        .filter-condition select,
        .filter-condition input,
        .filter-condition button {
            min-width: 0;
            box-sizing: border-box;
        }

        .filter-connector {
            width: 90px;
            margin: 0.15rem 0 0.15rem 0;
        }

        .filter-actions {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.75rem;
            margin-top: 0.75rem;
        }

        .filter-actions button,
        .filter-condition button {
            cursor: pointer;
        }

        .filter-result-count {
            font-weight: 500;
            margin-left: auto;
        }

        .filter-empty {
            padding: 1rem;
            text-align: center;
        }

        .mod-card[hidden] {
            display: none;
        }

        .mod-art {
            position: relative;
        }

        /* Character portrait is deliberately kept below the mod artwork/icon layer. */
        .mod-character {
            position: absolute;
            z-index: 3;
            left: -5px;
            bottom: -5px;
            width: 48px;
            height: 48px;
            border-radius: 50%;
            overflow: hidden;
            background: rgba(0, 0, 0, 0.75);
            border: 2px solid rgba(255, 255, 255, 0.9);
            box-sizing: border-box;
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.65);
        }

        .mod-character img {
            display: block;
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .mods-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
            gap: 1rem;
        }

        .mod-card {
            position: relative;
            padding: 0.9rem;
            margin: 0;
            min-height: 280px;
        }

        .mod-card-title {
            text-align: center;
            font-size: 18px;
            font-weight: 500;
            margin-bottom: 0.5rem;
            text-transform: capitalize;
        }

        /*
         * SWGOH mod shape atlas:
         * 1080 x 450 pixels, 12 columns x 5 rows, 90 x 90 pixel cells.
         * Columns 0-5 are normal shapes and columns 6-11 are gold shapes.
         */
        .mod-art {
            width: 90px;
            height: 90px;
            margin: 0 auto 0.75rem;
            background-image: url('IMAGES/MODS/mod-shape-atlas.png');
            background-size: 1080px 450px;
            background-position:
                calc(var(--shape-x) * -90px)
                calc(var(--shape-y) * -90px);
            background-repeat: no-repeat;
        }

        /*
         * SWGOH mod icon atlas:
         * 256 x 160 pixels, 8 columns x 5 rows, 32 x 32 pixel cells.
         */
        .mod-art::after {
            content: '';
            position: absolute;
            width: 32px;
            height: 32px;

            /* Default: centered */
            left: 29px;
            top: 29px;

            background-image: url('IMAGES/MODS/mod-icon-atlas.png');
            background-size: 256px 160px;
            background-position:
                calc(var(--icon-x) * -32px)
                calc(var(--icon-y) * -32px);
            background-repeat: no-repeat;
        }

        /* Position the set icon in the black area of each mod shape */

        /* Square */
        .mod-card[data-slot="2"] .mod-art::after {
            left: 36px;
            top: 23px;
        }

        /* Arrow */
        .mod-card[data-slot="3"] .mod-art::after {
            left: 39px;
            top: 20px;
        }

        /* Diamond */
        .mod-card[data-slot="4"] .mod-art::after {
            left: 29px;
            top: 29px;
        }

        /* Triangle */
        .mod-card[data-slot="5"] .mod-art::after {
            left: 29px;
            top: 34px;
        }

        /* Circle */
        .mod-card[data-slot="6"] .mod-art::after {
            left: 29px;
            top: 29px;
        }

        /* Cross */
        .mod-card[data-slot="7"] .mod-art::after {
            left: 29px;
            top: 29px;
        }

        .mod-details {
            text-align: center;
            line-height: 1.5;
        }

        .mod-details span {
            margin: 0 0.25rem;
        }

        @media only screen and (max-width: 600px) {
            .filter-condition {
                grid-template-columns: 1fr 1fr;
            }

            .filter-condition select,
            .filter-condition input,
            .filter-condition button {
                width: 100%;
            }

            .filter-connector {
                width: 100%;
            }

            .filter-result-count {
                margin-left: 0;
                width: 100%;
            }

            .mods-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }

            .mod-art {
                width: 70px;
                height: 70px;
                background-size: 840px 350px;
                background-position:
                    calc(var(--shape-x) * -70px)
                    calc(var(--shape-y) * -70px);
            }

            .mod-art::after {
                width: 25px;
                height: 25px;
                left: 22px;
                top: 22px;
                background-size: 200px 125px;
                background-position:
                    calc(var(--icon-x) * -25px)
                    calc(var(--icon-y) * -25px);
            }

            /* Position the set icon in the black area of each mod shape */
            .mod-card[data-slot="2"] .mod-art::after {
                left: 28px;
                top: 18px;
            }

            .mod-card[data-slot="3"] .mod-art::after {
                left: 30px;
                top: 16px;
            }

            .mod-card[data-slot="4"] .mod-art::after {
                left: 22px;
                top: 22px;
            }

            .mod-card[data-slot="5"] .mod-art::after {
                left: 22px;
                top: 26px;
            }

            .mod-card[data-slot="6"] .mod-art::after {
                left: 22px;
                top: 22px;
            }

            .mod-card[data-slot="7"] .mod-art::after {
                left: 22px;
                top: 22px;
            }

            .mod-character {
                width: 40px;
                height: 40px;
                left: -3px;
                bottom: -3px;
            }
        }
    </style>
</head>
<body>
<div class="site-container">
    <div class="site-pusher">
        <?php include 'navbar.php'; ?>

        <div class="site-content">
            <div class="container">
                <?php include 'pheader.php'; ?>

                <h3>Player Mods</h3>

                <div class="card mod-filter">
                    <div class="mod-filter-header" id="mod-filter-header" role="button" tabindex="0" aria-expanded="true">
                        <div>
                            <h4>Filter mods</h4>
                            <div class="mod-filter-summary" id="filter-summary">No filters applied</div>
                        </div>
                        <span class="material-icons" id="filter-toggle-icon">expand_less</span>
                    </div>

                    <div class="mod-filter-body" id="mod-filter-body">
                        <div id="filter-conditions"></div>

                        <div class="filter-actions">
                            <button type="button" id="add-filter">+ Add condition</button>
                            <button type="button" id="clear-filters">Clear filters</button>
                            <span class="filter-result-count" id="filter-result-count"></span>
                        </div>
                    </div>
                </div>

                <div class="mods-grid" id="mods-grid">
<?php foreach ($mods as $mod): ?>
<?php
    $slot = (int) $mod['slot'];
    $mod_set = (int) $mod['mod_set'];
    $pips = (int) $mod['pips'];
    $tier = (int) $mod['tier'];
    $level = (int) $mod['level'];
    $def_id = (string) ($mod['defId'] ?? '');

    $slot_name = $slot_names[$slot] ?? 'unknown';
    $set_name = $set_names[$mod_set] ?? 'unknown';

    // Slots 2-7 map to the six shape columns.
    $slot_index = max(0, min(5, $slot - 2));

    // The gold shape is the 6-dot variant (columns 6-11).
    $shape_index = $slot_index + ($pips >= 6 ? 6 : 0);

    // Both atlases use the same five color/tier rows.
    $tier_index = max(0, min(4, $tier - 1));

    // Mod sets 1-8 map directly to the eight icon columns.
    $icon_index = max(0, min(7, $mod_set - 1));
?>
                    <div
                        class="card mod-card"
                        data-slot="<?php echo h($slot); ?>"
                        data-set="<?php echo h($mod_set); ?>"
                        data-pips="<?php echo h($pips); ?>"
                        data-level="<?php echo h($level); ?>"
                        data-tier="<?php echo h($tier); ?>"
                        data-defid="<?php echo h($def_id); ?>"
                    >
                        <div class="mod-card-title">
                        </div>
                        <div class="mod-details">
                            <span><?php echo str_repeat('★', $pips);?></span>
                            <span>Lvl <?php echo h($level); ?></span>
                        </div>

                        <div
                            class="mod-art"
                            style="--shape-x: <?php echo $shape_index; ?>; --shape-y: <?php echo $tier_index; ?>; --icon-x: <?php echo $icon_index; ?>; --icon-y: <?php echo $tier_index; ?>;"
                            role="img"
                            aria-label="<?php echo h($set_name . ' ' . $slot_name); ?> mod"
                        >
<?php if ($def_id !== ''): ?>
                            <div class="mod-character" title="<?php echo h($def_id); ?>">
                                <img
                                    src="IMAGES/CHARACTERS/<?php echo rawurlencode($def_id); ?>.png"
                                    alt="<?php echo h($def_id); ?>"
                                    loading="lazy"
                                    onerror="this.parentElement.style.display='none';"
                                >
                            </div>
<?php endif; ?>
                        </div>

                    </div>
<?php endforeach; ?>
                </div>

                <div class="card filter-empty" id="filter-empty" hidden>
                    No mods match the selected filters.
                </div>

                <?php if (empty($mods)): ?>
                    <div class="card">
                        No mods found.
                    </div>
                <?php endif; ?>
            </div>
        </div>

        <div class="site-cache" id="site-cache"></div>
    </div>
</div>

<script>
(function () {
    'use strict';

    const conditionsContainer = document.getElementById('filter-conditions');
    const addFilterButton = document.getElementById('add-filter');
    const clearFiltersButton = document.getElementById('clear-filters');
    const resultCount = document.getElementById('filter-result-count');
    const filterSummary = document.getElementById('filter-summary');
    const filterHeader = document.getElementById('mod-filter-header');
    const filterBody = document.getElementById('mod-filter-body');
    const filterToggleIcon = document.getElementById('filter-toggle-icon');
    const filterEmpty = document.getElementById('filter-empty');
    const cards = Array.from(document.querySelectorAll('.mod-card'));

    const slotOptions = <?php echo json_encode($slot_names, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE); ?>;
    const setOptions = <?php echo json_encode($set_names, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE); ?>;
    const characterOptions = <?php echo json_encode($character_ids, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE); ?>;

    const fieldDefinitions = {
        character: {
            label: 'Character',
            type: 'select',
            values: characterOptions
        },
        slot: {
            label: 'Slot',
            type: 'select',
            values: Object.entries(slotOptions).map(([value, label]) => ({ value, label }))
        },
        set: {
            label: 'Set',
            type: 'select',
            values: Object.entries(setOptions).map(([value, label]) => ({ value, label }))
        },
        pips: { label: 'Pips', type: 'number' },
        level: { label: 'Level', type: 'number' },
        tier: { label: 'Tier', type: 'number' }
    };

    let conditionId = 0;

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function makeValueControl(field, id) {
        const definition = fieldDefinitions[field];

        if (definition.type === 'number') {
            return '<input type="number" class="filter-value" id="filter-value-' + id + '" step="1" placeholder="Value">';
        }

        let html = '<select class="filter-value" id="filter-value-' + id + '">';
        html += '<option value="">Select...</option>';

        if (field === 'character') {
            characterOptions.forEach(function (value) {
                html += '<option value="' + escapeHtml(value) + '">' + escapeHtml(value) + '</option>';
            });
        } else {
            definition.values.forEach(function (item) {
                const value = typeof item === 'object' ? item.value : item;
                const label = typeof item === 'object' ? item.label : item;
                html += '<option value="' + escapeHtml(value) + '">' + escapeHtml(label) + '</option>';
            });
        }

        html += '</select>';
        return html;
    }

    function makeCondition(field, connector) {
        const id = ++conditionId;
        const definition = fieldDefinitions[field];
        const isNumber = definition.type === 'number';

        const wrapper = document.createElement('div');
        wrapper.className = 'filter-condition-wrapper';
        wrapper.dataset.conditionId = id;

        if (conditionsContainer.children.length > 0) {
            const connectorSelect = document.createElement('select');
            connectorSelect.className = 'filter-connector';
            connectorSelect.setAttribute('aria-label', 'Combine with previous condition');
            connectorSelect.innerHTML = '<option value="AND">AND</option><option value="OR">OR</option>';
            connectorSelect.value = connector || 'AND';
            connectorSelect.addEventListener('change', applyFilters);
            wrapper.appendChild(connectorSelect);
        }

        const row = document.createElement('div');
        row.className = 'filter-condition';

        const fieldSelect = document.createElement('select');
        fieldSelect.className = 'filter-field';
        fieldSelect.setAttribute('aria-label', 'Filter characteristic');
        Object.entries(fieldDefinitions).forEach(function ([key, item]) {
            const option = document.createElement('option');
            option.value = key;
            option.textContent = item.label;
            option.selected = key === field;
            fieldSelect.appendChild(option);
        });

        const operatorSelect = document.createElement('select');
        operatorSelect.className = 'filter-operator';
        operatorSelect.setAttribute('aria-label', 'Filter operator');
        const operators = isNumber ? ['=', '!=', '>=', '<=', '>', '<'] : ['='];
        operators.forEach(function (operator) {
            const option = document.createElement('option');
            option.value = operator;
            option.textContent = operator;
            operatorSelect.appendChild(option);
        });

        const valueContainer = document.createElement('div');
        valueContainer.className = 'filter-value-container';
        valueContainer.innerHTML = makeValueControl(field, id);

        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.textContent = 'Remove';
        removeButton.addEventListener('click', function () {
            wrapper.remove();
            normalizeConnectors();
            applyFilters();
        });

        fieldSelect.addEventListener('change', function () {
            const newField = fieldSelect.value;
            const newDefinition = fieldDefinitions[newField];
            operatorSelect.innerHTML = '';
            (newDefinition.type === 'number' ? ['=', '!=', '>=', '<=', '>', '<'] : ['=']).forEach(function (operator) {
                const option = document.createElement('option');
                option.value = operator;
                option.textContent = operator;
                operatorSelect.appendChild(option);
            });
            valueContainer.innerHTML = makeValueControl(newField, id);
            valueContainer.querySelector('.filter-value').addEventListener('change', applyFilters);
            valueContainer.querySelector('.filter-value').addEventListener('input', applyFilters);
            applyFilters();
        });

        operatorSelect.addEventListener('change', applyFilters);

        row.appendChild(fieldSelect);
        row.appendChild(operatorSelect);
        row.appendChild(valueContainer);
        row.appendChild(removeButton);
        wrapper.appendChild(row);
        conditionsContainer.appendChild(wrapper);

        const valueControl = valueContainer.querySelector('.filter-value');
        valueControl.addEventListener('change', applyFilters);
        valueControl.addEventListener('input', applyFilters);

        applyFilters();
    }

    function normalizeConnectors() {
        const wrappers = Array.from(conditionsContainer.children);
        wrappers.forEach(function (wrapper, index) {
            const connector = wrapper.querySelector('.filter-connector');
            if (index === 0 && connector) {
                connector.remove();
            }
            if (index > 0 && !connector) {
                const connectorSelect = document.createElement('select');
                connectorSelect.className = 'filter-connector';
                connectorSelect.innerHTML = '<option value="AND">AND</option><option value="OR">OR</option>';
                connectorSelect.addEventListener('change', applyFilters);
                wrapper.insertBefore(connectorSelect, wrapper.firstChild);
            }
        });
    }

    function getConditions() {
        return Array.from(conditionsContainer.children).map(function (wrapper, index) {
            const field = wrapper.querySelector('.filter-field').value;
            const operator = wrapper.querySelector('.filter-operator').value;
            const value = wrapper.querySelector('.filter-value').value;
            const connector = index === 0 ? null : wrapper.querySelector('.filter-connector').value;
            return { field, operator, value, connector };
        });
    }

    function compare(actual, operator, expected) {
        if (actual === null || actual === undefined || expected === '') {
            return false;
        }

        if (['pips', 'level', 'tier'].includes(arguments[3])) {
            actual = Number(actual);
            expected = Number(expected);
        }

        switch (operator) {
            case '=': return actual == expected;
            case '!=': return actual != expected;
            case '>=': return actual >= expected;
            case '<=': return actual <= expected;
            case '>': return actual > expected;
            case '<': return actual < expected;
            default: return false;
        }
    }

    function conditionMatches(card, condition) {
        if (!condition.value) {
            return true;
        }

        let actual;
        switch (condition.field) {
            case 'character': actual = card.dataset.defid; break;
            case 'slot': actual = card.dataset.slot; break;
            case 'set': actual = card.dataset.set; break;
            case 'pips': actual = Number(card.dataset.pips); break;
            case 'level': actual = Number(card.dataset.level); break;
            case 'tier': actual = Number(card.dataset.tier); break;
            default: return true;
        }

        if (['pips', 'level', 'tier'].includes(condition.field)) {
            const expected = Number(condition.value);
            switch (condition.operator) {
                case '=': return actual === expected;
                case '!=': return actual !== expected;
                case '>=': return actual >= expected;
                case '<=': return actual <= expected;
                case '>': return actual > expected;
                case '<': return actual < expected;
                default: return false;
            }
        }

        return condition.operator === '=' && actual === condition.value;
    }

    function formatCondition(condition) {
        const labels = {
            character: 'Character',
            slot: 'Slot',
            set: 'Set',
            pips: 'Pips',
            level: 'Level',
            tier: 'Tier'
        };

        let value = condition.value;
        if (condition.field === 'slot') {
            value = slotOptions[value] || value;
        } else if (condition.field === 'set') {
            value = setOptions[value] || value;
        }

        return labels[condition.field] + ' ' + condition.operator + ' ' + value;
    }

    function applyFilters() {
        const conditions = getConditions().filter(function (condition) {
            return condition.value !== '';
        });

        let visibleCount = 0;

        cards.forEach(function (card) {
            if (conditions.length === 0) {
                card.hidden = false;
                visibleCount++;
                return;
            }

            // Conditions are evaluated from left to right, making the displayed
            // AND/OR connector the exact logical operation used by the filter.
            let matches = conditionMatches(card, conditions[0]);
            for (let i = 1; i < conditions.length; i++) {
                const current = conditionMatches(card, conditions[i]);
                matches = conditions[i].connector === 'OR'
                    ? matches || current
                    : matches && current;
            }

            card.hidden = !matches;
            if (matches) {
                visibleCount++;
            }
        });

        const total = cards.length;
        resultCount.textContent = visibleCount + ' / ' + total + ' mods';
        filterEmpty.hidden = visibleCount !== 0 || total === 0;

        if (conditions.length === 0) {
            filterSummary.textContent = 'No filters applied';
        } else {
            filterSummary.textContent = conditions.map(function (condition, index) {
                return (index > 0 ? ' ' + condition.connector + ' ' : '') + formatCondition(condition);
            }).join('');
        }
    }

    addFilterButton.addEventListener('click', function () {
        const connector = conditionsContainer.children.length > 0 ? 'AND' : null;
        makeCondition('slot', connector);
    });

    clearFiltersButton.addEventListener('click', function () {
        conditionsContainer.innerHTML = '';
        applyFilters();
    });

    function toggleFilterPanel() {
        const expanded = filterBody.hidden;
        filterBody.hidden = !expanded;
        filterHeader.setAttribute('aria-expanded', String(expanded));
        filterToggleIcon.textContent = expanded ? 'expand_less' : 'expand_more';
    }

    filterHeader.addEventListener('click', toggleFilterPanel);
    filterHeader.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            toggleFilterPanel();
        }
    });

    // Start with one condition so the filter is immediately discoverable.
    makeCondition('slot', null);
})();
</script>
</body>
<?php include 'sitefooter.php'; ?>
</html>
