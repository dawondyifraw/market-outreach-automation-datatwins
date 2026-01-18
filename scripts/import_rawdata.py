#!/usr/bin/env python
"""
Import raw Dutch municipalities and employees data
Processes: Gemeenten.csv and medewerkers_Gemeenten.csv
"""

import csv
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from sqlmodel import Session, select
from app.database import engine, init_db
from app.models import Target, Contact
from scripts.role_translations import translate_role
import re


def extract_email(email_str: str) -> str | None:
    """Extract first email from semicolon-separated list"""
    if not email_str:
        return None
    emails = [e.strip() for e in email_str.split(";") if e.strip()]
    return emails[0] if emails else None


def extract_phone(phone_str: str) -> str | None:
    """Extract first phone from semicolon-separated list"""
    if not phone_str:
        return None
    phones = [p.strip() for p in phone_str.split(";") if p.strip() and not p.strip().startswith("label")]
    return phones[0] if phones else None


def extract_province(adressen_str: str) -> str | None:
    """Extract province abbreviation (provincieAfkorting) from address field"""
    if not adressen_str:
        return None
    # Look for provincieAfkorting: XX pattern
    match = re.search(r'provincieAfkorting:\s*([A-Z]{2})', adressen_str)
    if match:
        return match.group(1)
    return None


def import_gemeenten():
    """Import municipalities from Gemeenten.csv"""
    print("📥 Importing municipalities from Gemeenten.csv...")
    
    path = Path("rawdata/Gemeenten.csv")
    if not path.exists():
        print(f"❌ File not found: {path}")
        return 0
    
    session = Session(engine)
    imported = 0
    skipped = 0
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            
            for row in reader:
                try:
                    # Extract key fields
                    name = row.get("Officiële naam", "").strip()
                    if not name:
                        skipped += 1
                        continue
                    
                    email = extract_email(row.get("E-mail adressen", ""))
                    phone = extract_phone(row.get("Telefoonnummers ", ""))
                    province = extract_province(row.get("Adressen (type, toelichting, straat, huisnummer, toevoeging, postbus, postcode, plaats, regio, provincieAfkorting, land, centroideLatitude, centroideLongitude, centroideRdx, centroideRdy)", ""))
                    website = row.get("Internetpagina's", "").strip() or None
                    
                    # Check if already exists
                    existing = session.exec(
                        select(Target).where(Target.name == name)
                    ).first()
                    
                    if existing:
                        # Update existing
                        existing.general_email = email or existing.general_email
                        existing.phone = phone or existing.phone
                        existing.province = province or existing.province
                        existing.website = website or existing.website
                        session.add(existing)
                        skipped += 1
                    else:
                        # Create new
                        target = Target(
                            name=name,
                            type="municipality",
                            sector="Government",
                            province=province,
                            website=website,
                            general_email=email,
                            phone=phone,
                            source="Gemeenten.csv",
                            notes=f"Dutch municipality - {row.get('Officiële naam', '')}"
                        )
                        session.add(target)
                        imported += 1
                    
                    if (imported + skipped) % 50 == 0:
                        print(f"  ✓ Processed {imported + skipped} municipalities...")
                
                except Exception as e:
                    print(f"  ⚠ Error processing row: {e}")
                    skipped += 1
            
            session.commit()
    
    except Exception as e:
        print(f"❌ Error importing municipalities: {e}")
        session.rollback()
        return 0
    finally:
        session.close()
    
    print(f"✅ Municipalities imported: {imported} new, {skipped} skipped\n")
    return imported


def import_medewerkers():
    """Import employees/contacts from medewerkers_Gemeenten.csv"""
    print("📥 Importing employees from medewerkers_Gemeenten.csv...")
    
    path = Path("rawdata/medewerkers_Gemeenten.csv")
    if not path.exists():
        print(f"❌ File not found: {path}")
        return 0
    
    session = Session(engine)
    imported = 0
    skipped = 0
    municipality_cache = {}
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            
            for row in reader:
                try:
                    gemeente_name = row.get("Organisatie (onderdeel)", "").strip()
                    person_name = row.get("Naam", "").strip()
                    function = row.get("Functie", "").strip()
                    
                    if not gemeente_name or not person_name:
                        skipped += 1
                        continue
                    
                    # Find or cache target
                    if gemeente_name not in municipality_cache:
                        target = session.exec(
                            select(Target).where(Target.name == gemeente_name)
                        ).first()
                        municipality_cache[gemeente_name] = target
                    else:
                        target = municipality_cache[gemeente_name]
                    
                    if not target:
                        skipped += 1
                        continue
                    
                    # Check if contact already exists
                    existing = session.exec(
                        select(Contact).where(
                            (Contact.target_id == target.id) & 
                            (Contact.full_name == person_name)
                        )
                    ).first()
                    
                    if existing:
                        existing.role = function or existing.role
                        existing.role_en = translate_role(function) if function else existing.role_en
                        session.add(existing)
                        skipped += 1
                    else:
                        # Create new contact
                        contact = Contact(
                            target_id=target.id,
                            full_name=person_name,
                            role=function or "Employee",
                            role_en=translate_role(function) if function else "Employee",
                            confidence_score="high" if function else "medium"
                        )
                        session.add(contact)
                        imported += 1
                    
                    if (imported + skipped) % 500 == 0:
                        print(f"  ✓ Processed {imported + skipped} employees...")
                
                except Exception as e:
                    print(f"  ⚠ Error processing row: {e}")
                    skipped += 1
            
            session.commit()
    
    except Exception as e:
        print(f"❌ Error importing employees: {e}")
        session.rollback()
        return 0
    finally:
        session.close()
    
    print(f"✅ Employees imported: {imported} new, {skipped} skipped\n")
    return imported


def main():
    """Main import process"""
    print("=" * 60)
    print("🚀 IMPORTING DUTCH MUNICIPALITY DATA")
    print("=" * 60)
    print()
    
    # Initialize database
    init_db()
    print("✓ Database initialized\n")
    
    # Import data
    gemeente_count = import_gemeenten()
    medewerkers_count = import_medewerkers()
    
    # Summary
    print("=" * 60)
    print("📊 IMPORT SUMMARY")
    print("=" * 60)
    print(f"✅ Municipalities: {gemeente_count} imported")
    print(f"✅ Employees: {medewerkers_count} imported")
    print()
    print("✨ Raw data successfully imported!")
    print()


if __name__ == "__main__":
    main()
