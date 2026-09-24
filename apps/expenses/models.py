from django.db import models
from django.core.validators import MinValueValidator

from common.models import TimeStampedModel


class Expense(TimeStampedModel):

    class Category(models.TextChoices):
        FEED = "Feed", "Feed"
        MEDICATION = "Medication", "Medication"
        VACCINATION = "Vaccination", "Vaccination"
        VETERINARY_SERVICES = "Veterinary Services", "Veterinary Services"
        UTILITIES = "Utilities", "Utilities"
        ELECTRICITY = "Electricity", "Electricity"
        WATER = "Water", "Water"
        LABOUR = "Labour", "Labour"
        TRANSPORT = "Transport", "Transport"
        FUEL = "Fuel", "Fuel"
        MAINTENANCE = "Maintenance", "Maintenance"
        EQUIPMENT = "Equipment", "Equipment"
        FARM_SUPPLIES = "Farm Supplies", "Farm Supplies"
        CLEANING_SUPPLIES = "Cleaning Supplies", "Cleaning Supplies"
        DISINFECTANTS = "Disinfectants", "Disinfectants"
        POULTRY_HOUSE_REPAIRS = (
            "Poultry House Repairs",
            "Poultry House Repairs",
        )
        FARM_CONSTRUCTION = (
            "Farm Construction",
            "Farm Construction",
        )
        LAND_RENT = "Land/Rent", "Land/Rent"
        SECURITY = "Security", "Security"
        INSURANCE = "Insurance", "Insurance"
        LICENSES_PERMITS = (
            "Licenses & Permits",
            "Licenses & Permits",
        )
        COMMUNICATION = "Communication", "Communication"
        INTERNET = "Internet", "Internet"
        MARKETING_ADVERTISING = (
            "Marketing & Advertising",
            "Marketing & Advertising",
        )
        PACKAGING = "Packaging", "Packaging"
        EGG_TRAYS = "Egg Trays", "Egg Trays"
        SACKS_BAGS = "Sacks & Bags", "Sacks & Bags"
        STATIONERY = "Stationery", "Stationery"
        OFFICE_EXPENSES = "Office Expenses", "Office Expenses"
        BANK_CHARGES = "Bank Charges", "Bank Charges"
        MOBILE_MONEY_CHARGES = (
            "Mobile Money Charges",
            "Mobile Money Charges",
        )
        PROFESSIONAL_SERVICES = (
            "Professional Services",
            "Professional Services",
        )
        VETERINARY_CONSULTATION = (
            "Veterinary Consultation",
            "Veterinary Consultation",
        )
        WASTE_MANAGEMENT = (
            "Waste Management",
            "Waste Management",
        )
        PEST_CONTROL = "Pest Control", "Pest Control"
        DEPRECIATION = "Depreciation", "Depreciation"
        LOAN_INTEREST = "Loan Interest", "Loan Interest"
        TAXES = "Taxes", "Taxes"
        TRAINING = "Training", "Training"
        MISCELLANEOUS = "Miscellaneous", "Miscellaneous"
        OTHER = "Other", "Other"

    date = models.DateField()

    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.OTHER,
    )

    description = models.CharField(
        max_length=250
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    payment_method = models.CharField(
        max_length=30,
        default="cash"
    )

    reference = models.CharField(
        max_length=80,
        blank=True
    )

    notes = models.TextField(
        blank=True
    )

    def __str__(self):
        return f"{self.get_category_display()} - {self.amount}"