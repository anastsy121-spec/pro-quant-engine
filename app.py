'use strict';

/**
 * ==============================================================================
 * MATCH DATA STRUCTURE: Piratas Veracruz vs Cancun FC
 * Tournament: Liga de Expansion MX
 * ==============================================================================
 */

const matchDataPiratasCancun = Object.freeze({
  metadata: {
    tournament: "Liga de Expansion MX",
    homeTeam: "Piratas Veracruz",
    awayTeam: "Cancun FC",
    timeStatus: "2:00 (heute)"
  },
  
  teamStats: {
    avgGoalsScored: { home: 2.3, away: 1.8 },
    over25GoalsPercentage: { home: 70, away: 50 },
    bothTeamsScoredPercentage: { home: 60, away: 60 },
    firstHalfWinnerPercentage: { home: 60, away: 30 },
    firstHalfOver05Goals: { home: 90, away: 70 },
    secondHalfOver05Goals: { home: 90, away: 100 }
  },

  recentForm: {
    homeTeamRecent: [
      { date: "06/11/26", opponent: "Cancun FC", score: "1:1", result: "Draw" },
      { date: "01/11/26", opponent: "CD Tapatio", score: "1:1", result: "Draw" },
      { date: "25/10/26", opponent: "CSD Dorados...", score: "0:5", result: "Win" },
      { date: "18/10/26", opponent: "Tepatitlan FC", score: "3:0", result: "Win" },
      { date: "10/10/26", opponent: "Tlaxcala FC", score: "4:2", result: "Loss" }
    ],
    awayTeamRecent: [
      { date: "06/11/26", opponent: "Piratas Veracruz", score: "1:1", result: "Draw" },
      { date: "01/11/26", opponent: "Tampico Made...", score: "2:0", result: "Win" },
      { date: "24/10/26", opponent: "Tepatitlan FC", score: "0:4", result: "Win" },
      { date: "18/10/26", opponent: "Venados FC", score: "1:1", result: "Draw" },
      { date: "11/10/26", opponent: "CD Mineros de...", score: "2:2", result: "Draw" }
    ]
  },

  oddsMarkets: {
    standard1X2: {
      homeWin: 1.52,
      draw: 3.90,
      awayWin: 4.90
    },
    doubleChance: {
      homeOrDraw: 1.07,
      homeOrAway: 1.22,
      drawOrAway: 2.15
    },
    handicap: {
      h0_1: { home: 2.90, draw: 2.95, away: 2.15 },
      h1_0: { home: 1.08, draw: 6.80, away: 13.0 }
    },
    overUnderGoals: {
      goals2_5: { over: 1.67, under: 2.00 },
      goals1_5: { over: 1.17, under: 4.10 },
      goals3_5: { over: 2.80, under: 1.35 }
    }
  }
});
