Parse DSB Print Selv billetter
==============================

Simple Python script to parse PDF train tickets from DSB (the Danish Railways).

Provides a function `parse(t)` that takes the output of `pdftotext billet.pdf -` as a str
and returns a tuple with the following named parts:

* year, month, day: Date of departure
* from_h, from_m: Time of departure
* to_h, to_m: Time of arrival
* fra: Departure station
* til: Arrival station
* kontrol: "Kontrolnummer", some number that's printed on the tickets (only for PDFs with a train ticket)
* billettype: Type of train ticket (only for PDFs with a train ticket)
* tognr: Train number of seat reservation (only for PDFs with a seat reservation)
* vogn: Wagon number of seat reservation (only for PDFs with a seat reservation)
* plads: Comma-separated seat numbers of seat reservation (only for PDFs with a seat reservation)
* antal: Number of seats reserved (only for PDFs with a seat reservation)
* pladstype: Type of seat reservation (only for PDFs with a seat reservation)

If you run the script from the command line, it will search for PDFs starting with "2"
and rename them according to the result of parsing them.
