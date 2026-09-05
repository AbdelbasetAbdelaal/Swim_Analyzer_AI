"""
Population Taxonomy & Compatibility Engine Service.
Defines demographic cohorts and strict compatibility resolution without silent interpolation or cross-group copying.
"""
from dataclasses import dataclass
from enum import Enum

class AgeCohort(str, Enum):
    U10 = "U10"              # <= 10
    U11_U12 = "U11-U12"      # 11-12
    U13 = "U13"              # 13
    U14_U15 = "U14-U15"      # 14-15
    U16_U17 = "U16-U17"      # 16-17
    JUNIOR_18_20 = "18-20"   # 18-20
    SENIOR_21_25 = "21-25"   # 21-25
    ADULT_26_35 = "26-35"    # 26-35
    MASTERS_36_44 = "36-44"  # 36-44
    MASTERS_45_54 = "45-54"  # 45-54
    MASTERS_55_PLUS = "55+"  # 55+
    OPEN_ELITE = "Open/Elite"

class SexCategory(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    MIXED = "Mixed"

@dataclass
class DemographicCohort:
    age_cohort: AgeCohort
    sex: SexCategory
    raw_age: int

class PopulationTaxonomyService:
    """
    Service resolving athlete age & gender into standardized Demographic Cohorts.
    Enforces strict compatibility matching.
    """

    @staticmethod
    def resolve_cohort(age: int, gender: str) -> DemographicCohort:
        sex_enum = SexCategory.FEMALE if gender.strip().lower() in ["female", "f"] else SexCategory.MALE

        if age <= 10:
            ac = AgeCohort.U10
        elif age <= 12:
            ac = AgeCohort.U11_U12
        elif age == 13:
            ac = AgeCohort.U13
        elif age <= 15:
            ac = AgeCohort.U14_U15
        elif age <= 17:
            ac = AgeCohort.U16_U17
        elif age <= 20:
            ac = AgeCohort.JUNIOR_18_20
        elif age <= 25:
            ac = AgeCohort.SENIOR_21_25
        elif age <= 35:
            ac = AgeCohort.ADULT_26_35
        elif age <= 44:
            ac = AgeCohort.MASTERS_36_44
        elif age <= 54:
            ac = AgeCohort.MASTERS_45_54
        else:
            ac = AgeCohort.MASTERS_55_PLUS

        return DemographicCohort(age_cohort=ac, sex=sex_enum, raw_age=age)

    @staticmethod
    def is_compatible(athlete_cohort: DemographicCohort, reference_age_min: int, reference_age_max: int, reference_sex: str) -> bool:
        """
        Evaluates strict compatibility between an athlete cohort and a reference study.
        No male-to-female, adult-to-youth, or senior-to-masters cross-copying.
        """
        ref_sex = reference_sex.strip().lower()
        ath_sex = athlete_cohort.sex.value.lower()

        # Sex check
        if ref_sex not in ["mixed", ath_sex]:
            return False

        # Age check
        return reference_age_min <= athlete_cohort.raw_age <= reference_age_max
