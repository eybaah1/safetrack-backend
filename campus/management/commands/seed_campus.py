from django.core.management.base import BaseCommand
from campus.models import CampusLocation


# Matches your frontend CAMPUS_LOCATIONS + searchableLocations
SEED_DATA = [
    {
        "name": "JQB (Junior Quarters)",
        "location_type": "landmark",
        "area": "Commercial",
        "description": "Major campus transportation hub near Junior Quarters residential area.",
        "latitude": 6.6731,
        "longitude": -1.5672,
        "safety_rating": 4.2,
        "lighting": "Well lit",
        "security_presence": "Patrol available",
        "is_popular": True,
    },
    {
        "name": "Ayeduase Gate",
        "location_type": "gate",
        "area": "Ayeduase",
        "description": "Main gate towards Ayeduase township. High foot traffic at night.",
        "latitude": 6.6698,
        "longitude": -1.5645,
        "safety_rating": 3.8,
        "lighting": "Moderately lit",
        "security_presence": "Security post nearby",
        "is_popular": True,
    },
    {
        "name": "Hall 7 Junction",
        "location_type": "hostel",
        "area": "Residential",
        "description": "Junction near Hall 7 (Brunei). Common walking route at night.",
        "latitude": 6.6782,
        "longitude": -1.5689,
        "safety_rating": 3.5,
        "lighting": "Moderately lit",
        "security_presence": "Patrol available",
        "is_popular": True,
    },
    {
        "name": "Main Library",
        "location_type": "facility",
        "area": "Academic",
        "description": "KNUST Main Library. Students often leave late at night.",
        "latitude": 6.6738,
        "longitude": -1.5725,
        "safety_rating": 4.5,
        "lighting": "Well lit",
        "security_presence": "Security post nearby",
        "is_popular": True,
    },
    {
        "name": "Great Hall",
        "location_type": "facility",
        "area": "Central",
        "description": "Great Hall — central campus landmark.",
        "latitude": 6.6755,
        "longitude": -1.5745,
        "safety_rating": 4.0,
        "lighting": "Well lit",
        "security_presence": "Patrol available",
        "is_popular": False,
    },
    {
        "name": "Engineering Building",
        "location_type": "facility",
        "area": "Engineering",
        "description": "College of Engineering faculty buildings.",
        "latitude": 6.6721,
        "longitude": -1.5758,
        "safety_rating": 3.8,
        "lighting": "Moderately lit",
        "security_presence": "Security post nearby",
        "is_popular": False,
    },
    {
        "name": "KSB (KNUST School of Business)",
        "location_type": "academic",
        "area": "Academic",
        "description": "School of Business campus.",
        "latitude": 6.6768,
        "longitude": -1.5702,
        "safety_rating": 4.0,
        "lighting": "Well lit",
        "security_presence": "Patrol available",
        "is_popular": False,
    },
    {
        "name": "Brunei Area",
        "location_type": "hostel",
        "area": "Residential",
        "description": "Brunei hostel area. Popular but can be poorly lit in some sections.",
        "latitude": 6.6805,
        "longitude": -1.5678,
        "safety_rating": 3.2,
        "lighting": "Moderately lit",
        "security_presence": "Limited",
        "is_popular": True,
    },
    {
        "name": "Unity Hall",
        "location_type": "hostel",
        "area": "Residential",
        "description": "Unity Hall (Conti). Major campus hostel.",
        "latitude": 6.6750,
        "longitude": -1.5735,
        "safety_rating": 4.0,
        "lighting": "Well lit",
        "security_presence": "Patrol available",
        "is_popular": False,
    },
    {
        "name": "Queens Hall",
        "location_type": "hostel",
        "area": "Residential",
        "description": "Queens Hall — female hostel.",
        "latitude": 6.6748,
        "longitude": -1.5740,
        "safety_rating": 4.3,
        "lighting": "Well lit",
        "security_presence": "Security post nearby",
        "is_popular": False,
    },
    {
        "name": "Republic Hall",
        "location_type": "hostel",
        "area": "Residential",
        "description": "Republic Hall (Repub).",
        "latitude": 6.6752,
        "longitude": -1.5730,
        "safety_rating": 3.8,
        "lighting": "Moderately lit",
        "security_presence": "Patrol available",
        "is_popular": False,
    },
    {
        "name": "Gaza Hostel",
        "location_type": "hostel",
        "area": "Residential",
        "description": "Gaza Hostel area. Further from central campus.",
        "latitude": 6.6810,
        "longitude": -1.5660,
        "safety_rating": 3.0,
        "lighting": "Poorly lit",
        "security_presence": "Limited",
        "is_popular": False,
    },
    {
        "name": "Tech Junction",
        "location_type": "bus_stop",
        "area": "Engineering",
        "description": "Bus stop near Engineering faculty. Common transit point.",
        "latitude": 6.6715,
        "longitude": -1.5750,
        "safety_rating": 3.5,
        "lighting": "Moderately lit",
        "security_presence": "Patrol available",
        "is_popular": True,
    },
    {
        "name": "Casely-Hayford",
        "location_type": "academic",
        "area": "Faculty",
        "description": "Casely-Hayford lecture halls.",
        "latitude": 6.6740,
        "longitude": -1.5710,
        "safety_rating": 3.8,
        "lighting": "Moderately lit",
        "security_presence": "Limited",
        "is_popular": False,
    },
    {
        "name": "College of Science",
        "location_type": "academic",
        "area": "Faculty",
        "description": "Faculty of Physical and Computational Sciences.",
        "latitude": 6.6735,
        "longitude": -1.5695,
        "safety_rating": 3.7,
        "lighting": "Moderately lit",
        "security_presence": "Limited",
        "is_popular": False,
    },
    {
        "name": "KNUST Hospital",
        "location_type": "medical",
        "area": "Services",
        "description": "University hospital. Open 24/7.",
        "latitude": 6.6770,
        "longitude": -1.5680,
        "safety_rating": 4.5,
        "lighting": "Well lit",
        "security_presence": "Security post nearby",
        "is_popular": False,
    },
    {
        "name": "CCB (Central Classroom Block)",
        "location_type": "academic",
        "area": "Central",
        "description": "Central Classroom Block. Major lecture venue.",
        "latitude": 6.6745,
        "longitude": -1.5720,
        "safety_rating": 4.0,
        "lighting": "Well lit",
        "security_presence": "Patrol available",
        "is_popular": False,
    },
    {
        "name": "Independence Hall",
        "location_type": "hostel",
        "area": "Residential",
        "description": "Independence Hall (Conti).",
        "latitude": 6.6754,
        "longitude": -1.5738,
        "safety_rating": 3.9,
        "lighting": "Moderately lit",
        "security_presence": "Patrol available",
        "is_popular": False,
    },
    {
        "name": "Africa Hall",
        "location_type": "hostel",
        "area": "Residential",
        "description": "Africa Hall.",
        "latitude": 6.6760,
        "longitude": -1.5742,
        "safety_rating": 3.8,
        "lighting": "Moderately lit",
        "security_presence": "Limited",
        "is_popular": False,
    },
]


class Command(BaseCommand):
    help = "Seed the database with KNUST campus locations"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing locations before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            deleted_count, _ = CampusLocation.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"Deleted {deleted_count} existing location(s).")
            )

        created = 0
        skipped = 0

        for data in SEED_DATA:
            _, was_created = CampusLocation.objects.get_or_create(
                name=data["name"],
                defaults=data,
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Created: {created}, Skipped (already exist): {skipped}"
            )
        )