    <?php $guild = $_SESSION['guild']; ?>
    
    <h2><?php echo $guild['name']; ?></h2>

    <div class="card">
        <p style="color:green;display:inline"><?php echo ($isMyGuild ? 'You are '.($isOfficer ? 'an officer ' : '').'in this guild' : ''); ?><small><?php echo ($isMyGuild && !$isMyGuildConfirmed ? ' (to confirm your identity and access restricted guild data, please run <i>go.register &lt;allyCode&gt; confirm</i>)':''); ?></small>
        </p>
    </div>

    <h3 style="color:green;display:inline"><?php echo ($isBonusGuild ? 'You are a guest in this guild' : ''); ?></h3>
        
    <!-- graph -->
    
    <div class="row guild-header mb-10">
	    <div class="col s12 m8 l8">
		    <div class="card stat gp">
			    <div class="card-content">
				    <div class="card-title">Galactic Power</div>
                    <div class="stat-detail">
						<label>Total</label>
						<div class="value">
                            <span class="hide-on-large-only"><?php echo round($guild['gp']/1000000,1); ?>M</span>
                            <span class="hide-on-med-and-down"><?php echo number_format($guild['gp'], 0, ".", " "); ?></span>
						</div>
					</div>
			    </div>
                <div class="card-graph">
                    <canvas id="gp-graph"></canvas>
                    <div class="chartjs-tooltip" id="gp-tooltip-0"></div>
                </div>
            </div>
        </div>

        <div class="col s12 m4 14">
		    <div class="card stat player">
			    <div class="card-content">
                    <div class="card-title">Players</div>
                    <div class="stat-detail">
						<label>Total</label>
						<div class="value">
                            <?php echo $guild['players']; ?><small>/50</small>
						</div>
					</div>
                    <div class="card-graph">
                        <canvas id="nb-players-graph"></canvas>
                        <div class="chartjs-tooltip" id="nb-players-tooltip-0"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <style type="text/css">
        canvas{
            -moz-user-select: none;
            -webkit-user-select: none;
            -ms-user-select: none;
        }
        .chartjs-tooltip {
            opacity: 0;
            position: absolute;
            background: rgba(0, 0, 0, .7);
            color: white;
            border-radius: 3px;
            -webkit-transition: all .1s ease;
            transition: all .1s ease;
            pointer-events: none;
            -webkit-transform: translate(-50%, 0);
            transform: translate(-50%, 0);
            padding: 4px;
            white-space: nowrap;
            z-index: 1000;
        }

        .card.stat {
            height: 166px !important;
        }
        .card.stat .card-content {
            height: 115px;
        }
        .card-graph {
            height: 50px;
            width: 100%;
        }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.7.2/Chart.min.js"></script>
    <script type="text/javascript">

	var gpChart = new Chart(document.getElementById("gp-graph").getContext('2d'), {
		type: 'line',
		data: {
			labels: [" <?php echo implode('", "', $guild['graph_date'])?>"],
			datasets: [{
				data: [ <?php echo implode(", ", $guild['graph_gp'])?> ],
				backgroundColor: 'rgba(255, 255, 255, 0.2)',
				pointBackgroundColor: 'rgba(255, 255, 255, 0.8)',
				borderColor: 'rgba(255, 255, 255, 0.8)',
				//borderWidth: 0
			}]
		},
		options: {
			responsive: true,
			maintainAspectRatio: false,
			elements : {
				point: {
					radius: 4,
					backgroundColor: 'rgba(255, 255, 255, 0.8)'
				}
			},
			animation: {
				duration: 0, // general animation time
			},
			legend: {
				display: false
			},
			scales: {
				xAxes: [{
					gridLines: false,
					ticks: {
						display: false,
					}
				}],
				yAxes: [{
					gridLines: false,
					ticks: {
						display: false,
					}
				}]
			}
		}
	});

	var nbPlayerChart = new Chart(document.getElementById("nb-players-graph").getContext('2d'), {
		type: 'bar',
		data: {
			labels: [" <?php echo implode('", "', $guild['graph_date'])?>"],
			datasets: [{
				data: [ <?php echo implode(", ", $guild['graph_players'])?> ],
				backgroundColor: 'rgba(255, 255, 255, 0.4)',
				borderWidth: 0
			}]
		},
		options: {
			responsive: true,
			maintainAspectRatio: false,
			animation: {
				duration: 0, // general animation time
			},
			legend: {
				display: false
			},
			scales: {
				xAxes: [{
					gridLines: false,
					ticks: {
						display: false,
					}
				}],
				yAxes: [{
					gridLines: false,
					ticks: {
						display: false,
						//beginAtZero:true
						min: 44,
						max: 50					}
				}]
			}
		}
	});
</script>
<!-- end graph -->

    <!-- Guild navigation Bar -->
    <?php include 'gnavbar.php' ; ?>
