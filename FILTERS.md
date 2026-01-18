# ✅ Advanced Filters & Search Added

## Overview

Targets can now be filtered and searched using multiple criteria simultaneously.

## Filter Capabilities

### 1. **Type Filter**

- Filter targets by type: Municipality, Employer
- Shows all municipalities or employers separately

### 2. **Status Filter**

- New, Contacted, Replied, Meeting, Won, Lost
- Track targets at each stage of the pipeline
- See pipeline overview with counts

### 3. **Province Filter**

- Filter by Dutch provinces (DR, NH, GD, FR, etc.)
- Limited to provinces with data
- Dropdown populated from database

### 4. **Sector Filter**

- Filter by business/organization sector
- Government, Technology, Healthcare, etc.
- Partial text matching (search within sector)

### 5. **Role Filter** ⭐ NEW

- Filter targets by employee roles
- Searches across both Dutch and English role names
- Examples:
  - Mayor / Burgemeester
  - Council Member / Raadslid
  - Alderman / Wethouder
  - Faction Leader / Fractievoorzitter

### 6. **Email Contact Filter**

- Has Email - targets with contact email
- No Email - targets without email
- Useful for outreach planning

### 7. **Full-Text Search**

- Searches across multiple fields:
  - Target name
  - Email address
  - Website
  - Sector
  - Notes
- Case-insensitive partial matching

## Usage Examples

### Example 1: Find Mayors in Drenthe

```
Province: DR
Role: Mayor
```

Result: All mayors in Drenthe province

### Example 2: Contacted employers with emails

```
Type: Employer
Status: Contacted
Email Contact: Has Email
```

Result: Contacted employers that have contact emails

### Example 3: Search for technology sector

```
Search: technology
Sector: Technology
```

Result: All targets in technology sector

### Example 4: Find Aldermen without contact info

```
Role: Alderman
Email Contact: No Email
```

Result: Aldermen whose municipalities lack email contacts

## API Parameters

### GET /targets

Query parameters:

- `target_type` - Type filter (employer, municipality)
- `status` - Status filter (new, contacted, replied, meeting, won, lost)
- `province` - Province code (e.g., DR, NH, UT)
- `sector` - Sector (partial match)
- `role` - Role name (partial match, searches both Dutch & English)
- `has_email` - Email filter (true/false)
- `search` - Full-text search
- `page` - Page number (default: 1, 20 results per page)

### Example API Calls

```bash
# Filter by province and role
curl "http://localhost:8000/targets?province=DR&role=Mayor"

# Search and filter
curl "http://localhost:8000/targets?search=Amsterdam&status=new"

# Multiple filters
curl "http://localhost:8000/targets?province=NH&has_email=true&target_type=municipality"

# Pagination
curl "http://localhost:8000/targets?page=2"
```

## Features

✅ **Combination Filtering** - Apply multiple filters together
✅ **Pagination** - 20 results per page with navigation
✅ **Dropdown Filters** - Dynamically populated from data
✅ **Text Search** - Full-text search across multiple fields
✅ **Bilingual Search** - Search by Dutch or English role names
✅ **Total Count** - Shows total matching results
✅ **Page Info** - Current page and total pages displayed
✅ **URL Persistence** - Filter state preserved in URLs

## Web UI

### Filter Panel

Located at top of targets list page with:

- 3-column grid layout
- 8 filter options
- Search button and Clear button
- Real-time dropdown population

### Results Display

- Shows total result count
- Current page / total pages
- Previous/Next pagination buttons
- 20 results per page
- Full target details (Name, Type, Status, Sector, Website)

## Database Queries

The system uses efficient SQL queries:

- Indexed lookups by province, type, status
- Subquery for role-based filtering
- OR conditions for full-text search
- Case-insensitive LIKE matching

## Performance

- Pagination: 20 results per page prevents data overload
- Indexed columns: Fast filtering on type, status
- Lazy loading: Only fetches needed data
- Dynamic dropdowns: Filtered from actual data values

## Combinations

### Most Useful Filter Combinations

1. **Province + Role**
   → Find key decision makers by location

2. **Status + Sector**
   → Track progress within industry vertical

3. **Type + Has Email**
   → Prepare contact lists for outreach

4. **Search + Status**
   → Find specific targets at certain stage

5. **Role + Status**
   → Identify untouched decision makers

## Technical Implementation

### Backend Changes

- Enhanced `list_targets()` endpoint with 6+ new parameters
- SQLModel WHERE clauses with OR, AND conditions
- Subquery for role-based filtering
- Pagination with offset/limit
- Dynamic dropdown value extraction

### Frontend Changes

- 3-column filter grid layout
- Dropdown selects populated from server data
- Clear filters button
- Pagination links with parameter preservation

### Database

- Existing indexes used for fast filtering
- No migration needed (uses existing columns)
- Efficient subquery for Contact role matching

## Next Steps

Users can now:

1. ✅ Browse targets with advanced filtering
2. ✅ Find targets by role and province
3. ✅ Segment by contact information availability
4. ✅ Search across all target attributes
5. ✅ Navigate paginated results
6. ✅ Combine filters for precise targeting

---

**Status**: ✅ **FILTERS FULLY IMPLEMENTED**

All filter combinations working. Ready for advanced target selection.
