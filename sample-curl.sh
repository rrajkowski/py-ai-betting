## ods API - Get Recent Scores for NCAAF (College Football)
curl --request GET \
        --url 'https://odds.p.rapidapi.com/v4/sports/upcoming/odds?regions=us&oddsFormat=american&markets=h2h%2Cspreads&dateFormat=iso' \
        --header 'x-rapidapi-host: odds.p.rapidapi.com' \
        --header 'x-rapidapi-key: ${RAPID_API_KEY}'
`[
    {
        "id": "b4e694771eec00d29e8b0e767fd89844",
        "sport_key": "americanfootball_ncaaf",
        "sport_title": "NCAAF",
        "commence_time": "2025-09-27T15:50:00Z",
        "home_team": "Kansas Jayhawks",
        "away_team": "Cincinnati Bearcats",
        "bookmakers": [
            {
                "key": "fanduel",
                "title": "FanDuel",
                "last_update": "2025-09-27T19:12:13Z",
                "markets": [
                    {
                        "key": "h2h",
                        "last_update": "2025-09-27T19:12:13Z",
                        "outcomes": [
                            {
                                "name": "Cincinnati Bearcats",
                                "price": 2.62
                            },
                            {
                                "name": "Kansas Jayhawks",
                                "price": 1.48
                            }
                        ]
                    },
                    {
                        "key": "spreads",
                        "last_update": "2025-09-27T19:12:13Z",
                        "outcomes": [
                            {
                                "name": "Cincinnati Bearcats",
                                "price": 2.06,
                                "point": 3.5
                            },
                            {
                                "name": "Kansas Jayhawks",
                                "price": 1.71,
                                "point": -3.5
                            }
                        ]
                    }
                ]
            },
            {
                "key": "draftkings",
                "title": "DraftKings",
                "last_update": "2025-09-27T19:12:12Z",
                "markets": [
                    {
                        "key": "h2h",
                        "last_update": "2025-09-27T19:12:12Z",
                        "outcomes": [
                            {
                                "name": "Cincinnati Bearcats",
                                "price": 2.6
                            },
                            {
                                "name": "Kansas Jayhawks",
                                "price": 1.48
                            }
                        ]
                    },
                    {
                        "key": "spreads",
                        "last_update": "2025-09-27T19:12:12Z",
                        "outcomes": [
                            {
                                "name": "Cincinnati Bearcats",
                                "price": 2,
                                "point": 3.5
                            },
                            {
                                "name": "Kansas Jayhawks",
                                "price": 1.77,
                                "point": -3.5
                            }
                        ]
                    }
                ]
            },
            {
                "key": "williamhill_us",
                "title": "Caesars",
                "last_update": "2025-09-27T19:07:11Z",
                "markets": [
                    {
                        "key": "h2h",
                        "last_update": "2025-09-27T19:07:11Z",
                        "outcomes": [
                            {
                                "name": "Cincinnati Bearcats",
                                "price": 1.83
                            },
                            {
                                "name": "Kansas Jayhawks",
                                "price": 1.91
                            }
                        ]
                    },
                    {
                        "key": "spreads",
                        "last_update": "2025-09-27T19:07:11Z",
                        "outcomes": [
                            {
                                "name": "Cincinnati Bearcats",
                                "price": 2,
                                "point": 3.5
                            },
                            {
                                "name": "Kansas Jayhawks",
                                "price": 1.77,
                                "point": -3.5
                            }
                        ]
                    }
                ]
            },
            {
                "key": "fanatics",
                "title": "Fanatics",
                "last_update": "2025-09-27T19:12:13Z",
                "markets": [
                    {
                        "key": "h2h",
                        "last_update": "2025-09-27T19:12:13Z",
                        "outcomes": [
                            {
                                "name": "Cincinnati Bearcats",
                                "price": 2.45
                            },
                            {
                                "name": "Kansas Jayhawks",
                                "price": 1.51
                            }
                        ]
                    }
                ]
            },
            {
                "key": "betmgm",
                "title": "BetMGM",
                "last_update": "2025-09-27T19:12:13Z",
                "markets": [
                    {
                        "key": "h2h",
                        "last_update": "2025-09-27T19:12:13Z",
                        "outcomes": [
                            {
                                "name": "Cincinnati Bearcats",
                                "price": 2.65
                            },
                            {
                                "name": "Kansas Jayhawks",
                                "price": 1.48
                            }
                        ]
                    },
                    {
                        "key": "spreads",
                        "last_update": "2025-09-27T19:12:13Z",
                        "outcomes": [
                            {
                                "name": "Cincinnati Bearcats",
                                "price": 2.05,
                                "point": 3.5
                            },
                            {
                                "name": "Kansas Jayhawks",
                                "price": 1.71,
                                "point": -3.5
                            }
                        ]
                    }
                ]
            },
            {
                "key": "bovada",
                "title": "Bovada",
                "last_update": "2025-09-27T19:07:18Z",
                "markets": [
                    {
                        "key": "h2h",
                        "last_update": "2025-09-27T19:07:18Z",
                        "outcomes": [
                            {
                                "name": "Cincinnati Bearcats",
                                "price": 1.87
                            },
                            {
                                "name": "Kansas Jayhawks",
                                "price": 1.87
                            }
                        ]
                    }
                ]
            }
        ]
    }
]``

curl --request GET \
	--url 'https://odds.p.rapidapi.com/v4/sports/americanfootball_ncaaf/scores?daysFrom=1' \
	--header 'x-rapidapi-host: odds.p.rapidapi.com' \
	--header 'x-rapidapi-key: ${RAPID_API_KEY}'


`[
    {
        "id": "0aa30bdb9295af4b13475b7aabb2cfea",
        "sport_key": "americanfootball_ncaaf",
        "sport_title": "NCAAF",
        "commence_time": "2025-09-26T23:05:00Z",
        "completed": true,
        "home_team": "Virginia Cavaliers",
        "away_team": "Florida State Seminoles",
        "scores": [
            {
                "name": "Virginia Cavaliers",
                "score": "46"
            },
            {
                "name": "Florida State Seminoles",
                "score": "38"
            }
        ],
        "last_update": "2025-09-27T19:15:49Z"
    }
]`