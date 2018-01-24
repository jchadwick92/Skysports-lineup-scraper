A programme used to find and email the team line ups as soon as they are announced and then email them.

It starts by updating my SQL database of players and assigning each player with an expected fantasy points score for that weekend.

It then goes to the Premier league fixtures on the Sky Sports website using BeautifulSoup and returns a dictionary which has a key of the match link and a value of the match time.

An hour before the match starts (when the lineups should be announced), it starts continuously scanning throug the link until the lineup is released.

Then it takes each player, runs it through my SQL database and subsequently emails you with the all the players in the starting lineup and their expected fantasy score.
