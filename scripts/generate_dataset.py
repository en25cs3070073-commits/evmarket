"""Generate the EV market dataset.

Vehicle identities, chemistries and body segments reflect real production models.
Numeric specification, sales and rating values are modelled approximations, not
observed measurements. See data/METADATA.md before citing any figure externally.
"""

import csv
import math
import random
import argparse
import os

random.seed(42)

YEARS = list(range(2018, 2026))
FIRST_YEAR, LAST_YEAR = YEARS[0], YEARS[-1]

# brand, model, country, body, segment, powertrain, chem, launch,
# base_kwh, wh_per_mi, base_price, peak_sales, peak_year,
# hp, accel, top_mph, seats, safety, peak_charge_kw, end_year
CATALOG = [
    ("Tesla", "Model 3", "China", "Sedan", "Mainstream", "BEV", "LFP", 2019, 60.0, 240, 41000, 210000, 2023, 283, 5.3, 140, 5, 5.0, 170, None),
    ("Tesla", "Model 3", "USA", "Sedan", "Mainstream", "BEV", "NMC", 2018, 75.0, 235, 46000, 155000, 2021, 358, 4.2, 140, 5, 5.0, 175, None),
    ("Tesla", "Model Y", "China", "SUV", "Mainstream", "BEV", "LFP", 2021, 60.0, 275, 36000, 420000, 2023, 299, 5.8, 130, 5, 5.0, 170, None),
    ("Tesla", "Model Y", "USA", "SUV", "Mainstream", "BEV", "NMC", 2020, 75.0, 265, 44000, 310000, 2023, 384, 4.3, 130, 5, 5.0, 175, None),
    ("Tesla", "Model S", "USA", "Sedan", "Luxury", "BEV", "NCA", 2018, 100.0, 265, 95000, 26000, 2021, 670, 3.1, 200, 5, 5.0, 250, None),
    ("Tesla", "Model X", "USA", "SUV", "Luxury", "BEV", "NCA", 2018, 100.0, 300, 98000, 22000, 2021, 670, 3.8, 155, 5, 5.0, 250, None),
    ("Tesla", "Cybertruck", "USA", "Truck", "Premium", "BEV", "NCA", 2023, 123.0, 380, 80000, 39000, 2025, 600, 4.1, 112, 5, 5.0, 250, None),
    ("BYD", "Atto 3", "China", "SUV", "Mainstream", "BEV", "LFP", 2022, 60.5, 245, 33000, 230000, 2024, 201, 7.5, 105, 5, 5.0, 88, None),
    ("BYD", "Seagull", "China", "Hatchback", "Budget", "BEV", "LFP", 2023, 38.8, 190, 11000, 340000, 2025, 54, 11.0, 62, 4, 4.0, 40, None),
    ("BYD", "Dolphin", "China", "Hatchback", "Budget", "BEV", "LFP", 2023, 60.4, 200, 16500, 210000, 2025, 94, 9.5, 99, 5, 5.0, 60, None),
    ("BYD", "Han EV", "China", "Sedan", "Premium", "BEV", "LFP", 2020, 85.0, 235, 32000, 120000, 2024, 512, 3.9, 115, 5, 5.0, 120, None),
    ("BYD", "Song Plus", "China", "SUV", "Mainstream", "BEV", "LFP", 2021, 71.8, 250, 23000, 260000, 2024, 218, 8.0, 105, 5, 5.0, 90, None),
    ("BYD", "Seal", "China", "Sedan", "Mainstream", "BEV", "LFP", 2023, 82.7, 230, 28000, 180000, 2025, 326, 5.9, 115, 5, 5.0, 150, None),
    ("BYD", "Yuan Pro", "China", "Hatchback", "Budget", "BEV", "LFP", 2018, 45.0, 205, 14000, 95000, 2021, 94, 10.5, 100, 5, 4.0, 60, 2022),
    ("BYD", "e6", "China", "Van", "Commercial", "BEV", "LFP", 2018, 72.0, 290, 30000, 45000, 2021, 121, 13.0, 90, 5, 4.0, 60, None),
    ("Wuling", "Hongguang Mini EV", "China", "Hatchback", "Budget", "BEV", "LFP", 2020, 13.0, 115, 5500, 410000, 2021, 27, 15.0, 62, 4, 3.0, 6, 2024),
    ("Wuling", "Bingo", "China", "SUV", "Budget", "BEV", "LFP", 2023, 45.0, 195, 10500, 70000, 2025, 68, 10.0, 99, 5, 4.0, 45, None),
    ("NIO", "ES6", "China", "SUV", "Premium", "BEV", "NMC", 2020, 75.0, 290, 51000, 95000, 2024, 544, 4.5, 124, 5, 5.0, 140, None),
    ("NIO", "ET7", "China", "Sedan", "Luxury", "BEV", "NMC", 2022, 100.0, 270, 58000, 45000, 2024, 653, 3.8, 124, 5, 5.0, 180, None),
    ("NIO", "ET7", "China", "Sedan", "Luxury", "BEV", "Semi-Solid-State", 2024, 150.0, 400, 85000, 2500, 2025, 653, 3.8, 124, 5, 5.0, 200, None),
    ("NIO", "ES8", "China", "SUV", "Luxury", "BEV", "Semi-Solid-State", 2024, 150.0, 430, 82000, 2200, 2025, 653, 4.1, 120, 6, 5.0, 200, None),
    ("NIO", "ET5", "China", "Sedan", "Premium", "BEV", "Semi-Solid-State", 2024, 150.0, 385, 52000, 3000, 2025, 496, 4.3, 130, 5, 5.0, 200, None),
    ("XPeng", "P7", "China", "Sedan", "Premium", "BEV", "NMC", 2021, 80.0, 230, 38000, 75000, 2023, 469, 4.3, 112, 5, 5.0, 175, None),
    ("XPeng", "G6", "China", "SUV", "Mainstream", "BEV", "LFP", 2023, 66.0, 250, 27000, 110000, 2025, 296, 6.3, 115, 5, 5.0, 280, None),
    ("Li Auto", "L7", "China", "SUV", "Premium", "EREV", "NMC", 2023, 42.0, 265, 42000, 160000, 2025, 443, 5.9, 110, 5, 5.0, 100, None),
    ("Zeekr", "001", "China", "Sedan", "Premium", "BEV", "NMC", 2022, 100.0, 265, 52000, 85000, 2025, 544, 3.8, 130, 5, 5.0, 200, None),
    ("Zeekr", "X", "China", "SUV", "Mainstream", "BEV", "LFP", 2023, 66.0, 245, 32000, 60000, 2025, 272, 6.9, 115, 5, 5.0, 130, None),
    ("Aion", "Y", "China", "SUV", "Budget", "BEV", "LFP", 2021, 63.0, 240, 20000, 180000, 2024, 134, 8.5, 100, 5, 5.0, 80, None),
    ("Aion", "S", "China", "Sedan", "Budget", "BEV", "LFP", 2019, 55.0, 215, 19000, 110000, 2022, 150, 8.0, 105, 5, 4.0, 70, None),
    ("Deepal", "SL03", "China", "Sedan", "Mainstream", "BEV", "NMC", 2022, 58.0, 225, 22000, 95000, 2025, 215, 6.5, 110, 5, 5.0, 90, None),
    ("Hongqi", "E-HS9", "China", "SUV", "Luxury", "BEV", "NMC", 2021, 120.0, 330, 60000, 15000, 2023, 551, 4.8, 112, 6, 5.0, 130, None),
    ("Yangwang", "U8", "China", "SUV", "Luxury", "BEV", "LFP", 2023, 135.0, 420, 150000, 12000, 2025, 1180, 3.6, 118, 5, 5.0, 160, None),
    ("Ora", "Good Cat", "China", "Hatchback", "Budget", "BEV", "LFP", 2021, 63.0, 210, 23000, 60000, 2023, 143, 9.0, 96, 5, 5.0, 65, None),
    ("JAC", "Yiwa", "China", "Hatchback", "Budget", "BEV", "Sodium-Ion", 2024, 25.0, 320, 11500, 28000, 2025, 61, 11.5, 64, 5, 4.0, 30, None),
    ("Foshan Bus", "T01 Sodium", "China", "Bus", "Commercial", "BEV", "Sodium-Ion", 2024, 250.0, 2200, 190000, 700, 2025, 150, 25.0, 60, 40, 4.0, 90, None),
    ("IM Motors", "L6", "China", "Sedan", "Premium", "BEV", "NMC", 2024, 90.0, 250, 31000, 42000, 2025, 295, 5.9, 130, 5, 5.0, 210, None),
    ("IM Motors", "L6 Solid-State", "China", "Sedan", "Luxury", "BEV", "Semi-Solid-State", 2024, 150.0, 340, 46000, 1200, 2025, 295, 5.9, 130, 5, 5.0, 210, None),
    ("MG", "4", "China", "Hatchback", "Mainstream", "BEV", "LFP", 2022, 64.0, 215, 30000, 140000, 2025, 170, 6.5, 105, 5, 5.0, 135, None),
    ("MG", "ZS EV", "India", "SUV", "Mainstream", "BEV", "LFP", 2021, 50.3, 230, 20000, 24000, 2024, 176, 8.0, 93, 5, 5.0, 70, None),
    ("MG", "Wuling Binguo", "China", "Hatchback", "Budget", "BEV", "LFP", 2023, 42.0, 195, 10000, 90000, 2025, 67, 11.0, 93, 5, 4.0, 40, None),
    ("Volkswagen", "ID.3", "Germany", "Hatchback", "Mainstream", "BEV", "NMC", 2020, 58.0, 205, 33000, 85000, 2023, 204, 7.3, 99, 5, 5.0, 120, None),
    ("Volkswagen", "ID.4", "Germany", "SUV", "Mainstream", "BEV", "NMC", 2021, 77.0, 265, 41000, 190000, 2024, 286, 8.5, 99, 5, 5.0, 135, None),
    ("Volkswagen", "ID.4", "USA", "SUV", "Mainstream", "BEV", "LFP", 2022, 62.0, 270, 39000, 60000, 2024, 201, 10.0, 99, 5, 5.0, 120, None),
    ("Volkswagen", "ID.7", "Germany", "Sedan", "Premium", "BEV", "NMC", 2024, 86.0, 245, 50000, 45000, 2025, 286, 6.7, 112, 5, 5.0, 175, None),
    ("Volkswagen", "ID. Buzz", "Germany", "Van", "Premium", "BEV", "NMC", 2022, 86.0, 330, 55000, 40000, 2025, 204, 10.0, 93, 5, 5.0, 170, None),
    ("Volkswagen", "e-Golf", "Germany", "Hatchback", "Budget", "BEV", "NMC", 2018, 35.8, 200, 31000, 25000, 2019, 134, 9.6, 87, 5, 5.0, 55, 2020),
    ("BMW", "i4", "Germany", "Sedan", "Premium", "BEV", "NMC", 2021, 81.0, 250, 52000, 65000, 2024, 335, 5.5, 118, 5, 5.0, 205, None),
    ("BMW", "iX", "Germany", "SUV", "Luxury", "BEV", "NMC", 2022, 100.0, 290, 87000, 40000, 2025, 516, 4.6, 124, 5, 5.0, 200, None),
    ("BMW", "iX1", "Germany", "SUV", "Premium", "BEV", "NMC", 2023, 64.7, 265, 45000, 55000, 2025, 201, 8.0, 112, 5, 5.0, 130, None),
    ("BMW", "i3", "Germany", "Hatchback", "Mainstream", "BEV", "NMC", 2018, 42.2, 215, 42000, 25000, 2019, 170, 7.0, 93, 4, 4.0, 50, 2022),
    ("Mercedes-Benz", "EQS", "Germany", "Sedan", "Luxury", "BEV", "NMC", 2021, 107.0, 260, 104000, 28000, 2024, 449, 4.1, 130, 5, 5.0, 200, None),
    ("Mercedes-Benz", "EQA", "Germany", "SUV", "Premium", "BEV", "NMC", 2021, 66.5, 265, 52000, 60000, 2024, 188, 8.5, 100, 5, 5.0, 100, None),
    ("Mercedes-Benz", "EQB", "Germany", "SUV", "Premium", "BEV", "NMC", 2022, 66.5, 280, 53000, 50000, 2025, 288, 6.2, 100, 5, 5.0, 100, None),
    ("Mercedes-Benz", "EQE", "Germany", "Sedan", "Luxury", "BEV", "NMC", 2022, 90.0, 255, 74000, 30000, 2025, 286, 6.0, 130, 5, 5.0, 170, None),
    ("Audi", "Q4 e-tron", "Germany", "SUV", "Premium", "BEV", "NMC", 2022, 77.0, 275, 49000, 70000, 2025, 201, 8.5, 112, 5, 5.0, 135, None),
    ("Audi", "Q8 e-tron", "Germany", "SUV", "Luxury", "BEV", "NMC", 2023, 106.0, 310, 74000, 32000, 2025, 402, 5.6, 118, 5, 5.0, 170, None),
    ("Audi", "e-tron GT", "Germany", "Sedan", "Luxury", "BEV", "NMC", 2021, 93.0, 260, 105000, 12000, 2023, 522, 3.3, 155, 4, 5.0, 270, None),
    ("Porsche", "Taycan", "Germany", "Sedan", "Luxury", "BEV", "NMC", 2020, 93.0, 255, 96000, 32000, 2023, 402, 4.6, 149, 4, 5.0, 270, None),
    ("Porsche", "Macan Electric", "Germany", "SUV", "Luxury", "BEV", "NMC", 2024, 100.0, 300, 85000, 14000, 2025, 355, 5.0, 140, 5, 5.0, 270, None),
    ("Opel", "Corsa Electric", "Germany", "Hatchback", "Budget", "BEV", "NMC", 2020, 50.0, 210, 30000, 45000, 2024, 134, 9.0, 93, 5, 4.0, 100, None),
    ("Skoda", "Enyaq", "Czechia", "SUV", "Mainstream", "BEV", "NMC", 2021, 77.0, 260, 42000, 90000, 2025, 201, 8.6, 99, 5, 5.0, 135, None),
    ("Cupra", "Born", "Spain", "Hatchback", "Mainstream", "BEV", "NMC", 2021, 58.0, 215, 37000, 40000, 2024, 201, 6.6, 99, 5, 5.0, 120, None),
    ("Seat", "Cupra El-Born", "Spain", "Hatchback", "Mainstream", "BEV", "NMC", 2021, 60.0, 210, 38000, 30000, 2023, 204, 7.0, 99, 5, 5.0, 120, 2023),
    ("Renault", "Megane E-Tech", "France", "SUV", "Mainstream", "BEV", "NMC", 2022, 60.0, 225, 37000, 65000, 2025, 218, 7.4, 99, 5, 5.0, 130, None),
    ("Renault", "Zoe", "France", "Hatchback", "Budget", "BEV", "NMC", 2018, 52.0, 210, 34000, 60000, 2019, 135, 11.0, 84, 5, 5.0, 50, 2024),
    ("Peugeot", "e-208", "France", "Hatchback", "Mainstream", "BEV", "NMC", 2019, 50.0, 200, 32000, 70000, 2023, 134, 8.3, 93, 5, 4.0, 100, None),
    ("Peugeot", "e-2008", "France", "SUV", "Mainstream", "BEV", "NMC", 2020, 50.0, 225, 35000, 55000, 2024, 134, 8.5, 93, 5, 4.0, 100, None),
    ("Citroen", "e-C3", "France", "Hatchback", "Budget", "BEV", "LFP", 2024, 44.0, 195, 24000, 45000, 2025, 115, 9.5, 84, 5, 4.0, 100, None),
    ("Dacia", "Spring", "France", "Hatchback", "Budget", "BEV", "LFP", 2021, 26.8, 175, 18000, 80000, 2024, 65, 13.8, 76, 5, 4.0, 30, None),
    ("Hyundai", "Ioniq 5", "South Korea", "SUV", "Mainstream", "BEV", "NMC", 2021, 77.0, 265, 42000, 160000, 2023, 225, 5.2, 115, 5, 5.0, 233, None),
    ("Hyundai", "Ioniq 6", "South Korea", "Sedan", "Mainstream", "BEV", "NMC", 2022, 77.0, 220, 40000, 75000, 2024, 225, 5.1, 115, 5, 5.0, 233, None),
    ("Hyundai", "Kona Electric", "South Korea", "SUV", "Mainstream", "BEV", "NMC", 2018, 64.0, 220, 33000, 65000, 2022, 201, 7.7, 105, 5, 5.0, 100, None),
    ("Hyundai", "Ioniq 5 N", "South Korea", "SUV", "Luxury", "BEV", "NMC", 2023, 84.0, 290, 66000, 18000, 2025, 641, 3.4, 161, 5, 5.0, 233, None),
    ("Kia", "EV6", "South Korea", "SUV", "Mainstream", "BEV", "NMC", 2022, 77.0, 255, 42000, 130000, 2024, 225, 5.2, 115, 5, 5.0, 233, None),
    ("Kia", "EV9", "South Korea", "SUV", "Premium", "BEV", "NMC", 2024, 99.8, 310, 55000, 45000, 2025, 201, 8.0, 118, 6, 5.0, 233, None),
    ("Kia", "Niro EV", "South Korea", "SUV", "Mainstream", "BEV", "NMC", 2019, 64.0, 230, 39000, 85000, 2024, 201, 7.8, 97, 5, 5.0, 100, None),
    ("Kia", "Soul EV", "South Korea", "Hatchback", "Mainstream", "BEV", "NMC", 2019, 64.0, 235, 33000, 40000, 2022, 201, 7.6, 97, 5, 5.0, 100, None),
    ("Kia", "EV5", "South Korea", "SUV", "Mainstream", "BEV", "LFP", 2024, 64.0, 250, 36000, 60000, 2025, 215, 6.9, 115, 5, 5.0, 175, None),
    ("Genesis", "GV60", "South Korea", "SUV", "Premium", "BEV", "NMC", 2022, 84.0, 280, 57000, 25000, 2025, 314, 4.5, 146, 5, 5.0, 233, None),
    ("Genesis", "G80 Electric", "South Korea", "Sedan", "Luxury", "BEV", "NMC", 2021, 94.5, 265, 82000, 12000, 2024, 365, 4.2, 146, 5, 5.0, 233, None),
    ("Nissan", "Leaf", "Japan", "Hatchback", "Budget", "BEV", "NMC", 2018, 40.0, 210, 28000, 45000, 2019, 148, 7.7, 90, 5, 4.0, 50, None),
    ("Nissan", "Leaf e+", "Japan", "Hatchback", "Mainstream", "BEV", "NMC", 2019, 62.0, 215, 33000, 28000, 2022, 214, 6.7, 93, 5, 4.0, 75, None),
    ("Nissan", "Ariya", "Japan", "SUV", "Mainstream", "BEV", "NMC", 2023, 87.0, 270, 40000, 55000, 2025, 317, 5.7, 99, 5, 5.0, 150, None),
    ("Toyota", "bZ4X", "Japan", "SUV", "Mainstream", "BEV", "NMC", 2022, 71.4, 285, 43000, 65000, 2025, 214, 6.8, 100, 5, 5.0, 150, None),
    ("Toyota", "bZ3", "China", "Sedan", "Mainstream", "BEV", "LFP", 2023, 65.0, 230, 23000, 70000, 2025, 182, 7.5, 100, 5, 5.0, 90, None),
    ("Mazda", "MX-30", "Japan", "SUV", "Mainstream", "BEV", "NMC", 2021, 35.5, 250, 34000, 18000, 2023, 143, 9.0, 93, 5, 5.0, 50, None),
    ("Honda", "Prologue", "USA", "SUV", "Premium", "BEV", "NMC", 2024, 85.0, 280, 48000, 45000, 2025, 288, 6.5, 110, 5, 5.0, 195, None),
    ("Honda", "e", "Japan", "Hatchback", "Budget", "BEV", "NMC", 2020, 35.5, 200, 33000, 9000, 2021, 136, 8.3, 90, 4, 4.0, 55, 2024),
    ("Volvo", "EX40", "Sweden", "SUV", "Premium", "BEV", "NMC", 2021, 82.0, 280, 50000, 70000, 2024, 232, 6.5, 112, 5, 5.0, 150, None),
    ("Volvo", "EC40", "Sweden", "SUV", "Premium", "BEV", "LFP", 2022, 69.0, 275, 53000, 50000, 2025, 235, 6.9, 112, 5, 5.0, 150, None),
    ("Volvo", "EX30", "Sweden", "SUV", "Mainstream", "BEV", "LFP", 2024, 64.0, 230, 36000, 60000, 2025, 268, 5.2, 112, 5, 5.0, 153, None),
    ("Polestar", "2", "Sweden", "Sedan", "Premium", "BEV", "NMC", 2020, 78.0, 250, 48000, 45000, 2023, 231, 6.2, 124, 5, 5.0, 155, None),
    ("Polestar", "3", "Sweden", "SUV", "Luxury", "BEV", "NMC", 2024, 111.0, 315, 73000, 15000, 2025, 483, 4.7, 140, 5, 5.0, 250, None),
    ("Smart", "#1", "China", "SUV", "Mainstream", "BEV", "LFP", 2022, 66.0, 255, 30000, 45000, 2025, 268, 6.7, 99, 4, 5.0, 130, None),
    ("Chevrolet", "Bolt EV", "USA", "Hatchback", "Budget", "BEV", "NMC", 2018, 65.0, 210, 31000, 45000, 2022, 200, 6.5, 91, 5, 4.0, 55, 2023),
    ("Chevrolet", "Equinox EV", "USA", "SUV", "Mainstream", "BEV", "LFP", 2024, 85.0, 260, 34000, 60000, 2025, 288, 6.0, 100, 5, 5.0, 195, None),
    ("Chevrolet", "Blazer EV", "USA", "SUV", "Premium", "BEV", "NMC", 2023, 102.0, 275, 45000, 30000, 2025, 340, 5.0, 110, 5, 5.0, 195, None),
    ("Cadillac", "LYRIQ", "USA", "SUV", "Luxury", "BEV", "NMC", 2023, 102.0, 310, 60000, 22000, 2025, 330, 5.7, 112, 5, 5.0, 195, None),
    ("Ford", "Mustang Mach-E", "USA", "SUV", "Premium", "BEV", "NMC", 2021, 88.0, 290, 43000, 90000, 2023, 480, 3.5, 130, 5, 5.0, 150, None),
    ("Ford", "F-150 Lightning", "USA", "Truck", "Premium", "BEV", "NMC", 2022, 131.0, 420, 50000, 40000, 2023, 580, 4.5, 110, 5, 5.0, 150, None),
    ("Rivian", "R1S", "USA", "SUV", "Luxury", "BEV", "NMC", 2022, 135.0, 390, 75000, 25000, 2025, 665, 3.5, 125, 5, 5.0, 220, None),
    ("Rivian", "R1T", "USA", "Truck", "Luxury", "BEV", "NMC", 2022, 135.0, 370, 73000, 20000, 2025, 665, 3.5, 125, 5, 5.0, 220, None),
    ("Lucid", "Air", "USA", "Sedan", "Luxury", "BEV", "NMC", 2021, 112.0, 215, 80000, 12000, 2024, 620, 3.3, 168, 5, 5.0, 300, None),
    ("VinFast", "VF 6", "Vietnam", "SUV", "Budget", "BEV", "LFP", 2023, 37.0, 215, 22000, 30000, 2025, 174, 8.0, 89, 5, 3.0, 60, None),
    ("VinFast", "VF 8", "Vietnam", "SUV", "Mainstream", "BEV", "NMC", 2022, 87.7, 290, 41000, 18000, 2024, 402, 5.5, 100, 5, 4.0, 110, None),
    ("Tata", "Nexon EV", "India", "SUV", "Mainstream", "BEV", "LFP", 2020, 40.6, 175, 14500, 40000, 2024, 143, 9.9, 80, 5, 5.0, 50, None),
    ("Tata", "Tiago EV", "India", "Hatchback", "Budget", "BEV", "LFP", 2023, 24.0, 125, 11000, 30000, 2025, 74, 12.0, 80, 5, 4.0, 35, None),
    ("Tata", "Punch EV", "India", "SUV", "Budget", "BEV", "LFP", 2024, 35.0, 145, 13000, 25000, 2025, 83, 11.0, 80, 5, 4.0, 45, None),
    ("Tata", "Curvv EV", "India", "SUV", "Mainstream", "BEV", "LFP", 2024, 45.0, 165, 18000, 20000, 2025, 148, 8.5, 90, 5, 5.0, 75, None),
    ("Mahindra", "XUV400", "India", "SUV", "Mainstream", "BEV", "NMC", 2022, 39.4, 170, 17000, 12000, 2024, 150, 8.6, 83, 5, 5.0, 50, None),
    ("Ather", "450X", "India", "Two-Wheeler", "Mainstream", "BEV", "NMC", 2021, 3.7, 22, 2300, 60000, 2025, 6, 4.0, 55, 2, 3.0, 1.2, None),
    ("Ola", "S1 Pro", "India", "Two-Wheeler", "Mainstream", "BEV", "NMC", 2023, 4.0, 24, 5000, 45000, 2025, 6, 4.0, 68, 2, 3.0, 1.5, None),
    ("TVS", "iQube", "India", "Two-Wheeler", "Budget", "BEV", "LFP", 2022, 3.4, 21, 1600, 55000, 2025, 4, 5.0, 43, 2, 3.0, 1.0, None),
    ("BYD", "K9 Electric Bus", "China", "Bus", "Commercial", "BEV", "LFP", 2018, 324.0, 2100, 330000, 14000, 2021, 240, 20.0, 62, 60, 4.0, 120, None),
    ("Yutong", "E12", "China", "Bus", "Commercial", "BEV", "LFP", 2018, 350.0, 2300, 310000, 11000, 2022, 240, 22.0, 62, 60, 4.0, 120, None),
    ("Tata", "Starbus EV", "India", "Bus", "Commercial", "BEV", "LFP", 2021, 145.0, 1400, 115000, 6000, 2025, 150, 25.0, 60, 40, 4.0, 90, None),
    ("Volvo", "7900 Electric", "Sweden", "Bus", "Commercial", "BEV", "NMC", 2019, 396.0, 2400, 580000, 1200, 2023, 240, 24.0, 62, 60, 4.0, 150, None),
    ("Freightliner", "eCascadia", "USA", "Truck", "Commercial", "BEV", "NMC", 2022, 552.0, 2200, 220000, 1500, 2025, 670, 18.0, 65, 2, 4.0, 300, None),
    ("Ford", "E-Transit", "USA", "Van", "Commercial", "BEV", "NMC", 2021, 68.0, 340, 52000, 25000, 2024, 265, 10.0, 80, 3, 4.0, 115, None),
    ("Mercedes-Benz", "eVito", "Germany", "Van", "Commercial", "BEV", "NMC", 2019, 60.0, 330, 60000, 12000, 2024, 113, 13.0, 90, 3, 4.0, 110, None),
]

# Real grid carbon intensity, kg CO2 per kWh. Source-level estimates, see METADATA.md.
GRID_INTENSITY = {
    "Norway": 0.03, "Sweden": 0.05, "France": 0.06, "Denmark": 0.07,
    "Brazil": 0.08, "Canada": 0.12, "Spain": 0.19, "United Kingdom": 0.21,
    "Germany": 0.36, "USA": 0.37, "Czechia": 0.41, "Italy": 0.32,
    "South Korea": 0.46, "Japan": 0.47, "Mexico": 0.42, "China": 0.55,
    "Thailand": 0.55, "India": 0.63, "Vietnam": 0.68, "Turkey": 0.45,
}

# Relative cradle-to-gate cell footprint, lithium-ion chemistries.
CHEM_EMISSION_FACTOR = {
    "LFP": 0.95, "NMC": 1.10, "NCA": 1.15,
    "Sodium-Ion": 0.85, "Semi-Solid-State": 1.30,
}

# Annual market expansion by calendar year, applied to all passenger segments.
MARKET_YEAR_FACTOR = {
    2018: 0.42, 2019: 0.52, 2020: 0.50, 2021: 0.78,
    2022: 1.00, 2023: 1.18, 2024: 1.22, 2025: 1.15,
}

BODY_EMISSION_BASE = {
    "Two-Wheeler": 0.9, "Hatchback": 4.2, "Sedan": 5.4, "SUV": 6.3,
    "Truck": 8.5, "Van": 6.8, "Bus": 18.0,
}

VARIANTS = {
    "Standard Range": {"kwh": 0.78, "whpm": 1.00, "price": 0.86, "hp": 0.72, "accel": 1.14, "share": 0.34},
    "Long Range": {"kwh": 1.00, "whpm": 0.96, "price": 1.00, "hp": 1.00, "accel": 1.00, "share": 0.48},
    "Performance": {"kwh": 1.00, "whpm": 1.10, "price": 1.14, "hp": 1.55, "accel": 0.79, "share": 0.18},
    "Base": {"kwh": 1.00, "whpm": 1.00, "price": 1.00, "hp": 1.00, "accel": 1.00, "share": 1.00},
}

# Tailpipe intensity and usage intensity by body type, used for the CO2e comparison.
ICE_KG_PER_KM = {
    "Two-Wheeler": 0.05, "Hatchback": 0.16, "Sedan": 0.175, "SUV": 0.20,
    "Van": 0.32, "Truck": 0.85, "Bus": 0.95,
}
ANNUAL_KM_BY_BODY = {
    "Two-Wheeler": 6000, "Hatchback": 13500, "Sedan": 13500, "SUV": 14000,
    "Van": 28000, "Truck": 65000, "Bus": 45000,
}


def variant_names(body, segment, chem):
    if body in ("Bus", "Van", "Two-Wheeler"):
        return ["Base"]
    if chem in ("Sodium-Ion", "Semi-Solid-State"):
        return ["Base"]
    if segment == "Budget":
        return ["Standard Range", "Long Range"]
    if segment == "Luxury":
        return ["Long Range", "Performance"]
    return ["Standard Range", "Long Range", "Performance"]


def sales_curve(launch, peak_year, end_year, year):
    if year < launch:
        return 0.0
    if end_year and year > end_year:
        return 0.0
    if peak_year <= launch:
        return max(0.10, math.exp(-0.22 * (year - launch)))
    if year <= peak_year:
        t = (year - launch) / (peak_year - launch)
        return 0.22 + 0.78 * (t ** 1.5)
    age = year - peak_year
    if end_year and year >= end_year:
        return max(0.08, math.exp(-0.40 * age))
    return max(0.12, math.exp(-0.22 * age))


def calibrate_ratings(rows):
    """Rank the composite quality score onto the 3.0-4.9 rating band."""
    vals = [r["_quality"] for r in rows]
    lo, hi = min(vals), max(vals)
    span = max(1e-9, hi - lo)
    for r in rows:
        norm = (r["_quality"] - lo) / span
        raw = 3.05 + 1.78 * (norm ** 0.9) + random.gauss(0, 0.05)
        r["customer_rating"] = round(min(4.9, max(3.0, raw)), 2)
        del r["_quality"]


def build_rows():
    rows = []
    for m in CATALOG:
        (brand, model, country, body, segment, powertrain, chem, launch,
         base_kwh, whpm, base_price, peak_sales, peak_year, hp, accel, top,
         seats, safety, kw, end_year) = m

        for year in YEARS:
            curve = sales_curve(launch, peak_year, end_year, year)
            if curve <= 0:
                continue

            age = year - launch
            cap_growth = 1.0 + min(0.22, 0.028 * max(0, age))
            deflation = 0.012 * min(age, 4) + 0.055 * max(0, min(age - 4, 3))
            price_factor = 1.0 - deflation
            grid = GRID_INTENSITY.get(country, 0.45)

            names = variant_names(body, segment, chem)
            shares = {n: VARIANTS[n]["share"] for n in names}
            total_share = sum(shares.values())
            model_units = (peak_sales * curve * MARKET_YEAR_FACTOR[year]
                           * random.uniform(0.88, 1.12))

            for vname in names:
                v = VARIANTS[vname]
                kwh_mult, whpm_mult = v["kwh"], v["whpm"]
                price_mult, hp_mult, accel_mult = v["price"], v["hp"], v["accel"]
                kwh = round(base_kwh * cap_growth * kwh_mult, 1)
                eff = whpm * whpm_mult * (1.0 - 0.006 * max(0, age))
                miles = kwh / (eff / 1000.0)
                price = base_price * price_factor * price_mult
                power = hp * hp_mult
                acc = accel * (1.0 / max(0.45, hp_mult ** 0.36)) * accel_mult
                t_speed = top * (1.06 if vname == "Performance" else 1.0)

                if miles < 45:
                    continue

                charge_min = (0.70 * kwh / max(kw, 0.5)) * 60 * 1.18

                units = max(50.0, model_units * shares[vname] / total_share
                            * random.uniform(0.94, 1.06))

                range_score = min(1.0, miles / 420.0)
                value_score = min(1.0, (miles / (price / 1000.0)) / 8.5)
                safety_score = (safety - 3.0) / 2.0
                charge_score = min(1.0, kw / 240.0)
                age_penalty = min(0.30, 0.040 * max(0, year - (peak_year or launch)))
                quality_term = (0.26 * range_score + 0.20 * value_score
                                + 0.18 * safety_score + 0.16 * charge_score
                                + 0.12 * random.random() + 0.08) - age_penalty

                mfg_co2 = (BODY_EMISSION_BASE[body]
                           + kwh * 0.066 * CHEM_EMISSION_FACTOR[chem]
                           * (0.70 + 0.55 * (grid / 0.60)))
                energy_per_km = (eff / 1000.0) / 1.60934
                annual_km = ANNUAL_KM_BY_BODY[body]
                ev_upstream = energy_per_km * annual_km * grid / 1000.0
                ice_tailpipe = ICE_KG_PER_KM[body] * annual_km / 1000.0

                rows.append({
                    "brand": brand,
                    "model": model,
                    "variant": vname,
                    "year": year,
                    "powertrain_type": powertrain,
                    "battery_technology": chem,
                    "body_type": body,
                    "market_segment": segment,
                    "country_of_origin": country,
                    "battery_capacity_kwh": round(kwh, 1),
                    "driving_range_miles": round(miles, 0),
                    "driving_range_km": round(miles * 1.60934, 0),
                    "energy_consumption_wh_per_mi": round(eff, 1),
                    "peak_charging_kw": round(kw * (1.0 if vname != "Performance" else 1.02), 1),
                    "charging_time_min_10_80": round(charge_min, 1),
                    "acceleration_0_60_mph": round(acc, 1),
                    "top_speed_mph": round(t_speed, 0),
                    "horsepower": round(power, 0),
                    "seating_capacity": seats,
                    "price_usd": round(price, -2),
                    "annual_sales_units": round(units, 0),
                    "customer_rating": 0.0,
                    "_quality": quality_term,
                    "safety_rating": safety,
                    "grid_intensity_kgco2_per_kwh": grid,
                    "estimated_manufacturing_co2e_tonnes": round(mfg_co2, 2),
                    "estimated_annual_co2e_saved_tonnes": round(
                        max(0.0, ice_tailpipe - ev_upstream), 2),
                })

    calibrate_ratings(rows)
    return rows


def write_country_table(path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["country", "grid_intensity_kgco2_per_kwh"])
        for c, v in sorted(GRID_INTENSITY.items()):
            w.writerow([c, v])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("data", "ev_market_dataset.csv"))
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    rows = build_rows()
    fields = list(rows[0].keys())

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    write_country_table(os.path.join("data", "country_grid_profile.csv"))

    brands = len({r["brand"] for r in rows})
    models = len({(r["brand"], r["model"]) for r in rows})
    total = sum(r["annual_sales_units"] for r in rows)
    print(f"rows={len(rows)} brands={brands} models={models} total_units={total:,.0f}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
