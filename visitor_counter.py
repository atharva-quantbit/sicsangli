# # sicsangli/visitor_counter.py
# import frappe
# import json
# import os
# from datetime import date

# FILE_PATH = os.path.join(frappe.get_app_path("sicsangli"), "visitor_counts.json")

# @frappe.whitelist(allow_guest=True)
# def record_visit(page_name=None):
#     if not page_name:
#         page_name = frappe.local.request.path or "unknown_page"

#     today = str(date.today())

#     if os.path.exists(FILE_PATH):
#         with open(FILE_PATH, "r", encoding="utf-8") as f:
#             data = json.load(f)
#     else:
#         data = {}

#     if page_name not in data:
#         data[page_name] = {}

#     if today not in data[page_name]:
#         data[page_name][today] = 0

#     data[page_name][today] += 1

#     with open(FILE_PATH, "w", encoding="utf-8") as f:
#         json.dump(data, f, ensure_ascii=False, indent=4)

#     return {"page": page_name, "date": today, "visits_today": data[page_name][today]}



import frappe
import json
import os
from datetime import date
from urllib.parse import urlparse

FILE_PATH = os.path.join(frappe.get_app_path("sicsangli"), "visitor_counts.json")

@frappe.whitelist(allow_guest=True)
def record_visit(page_url=None):
    frappe.logger().info(f"record_visit STARTED: url={page_url}, ip={getattr(frappe.local, 'request_ip', 'console')}")
    frappe.logger().info(f"FILE_PATH: {FILE_PATH}")
    
    path = urlparse(page_url).path if page_url else "/"
    today = str(date.today())
    ip = getattr(frappe.local, "request_ip", "console")
    return_dict = {
        "date": today,
        "total_visits_today": 0,
        "unique_ips": 0
    }
    
    try:
        if os.path.exists(FILE_PATH):
            with open(FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}
        
        if path not in data:
            data[path] = {}
        
        # Safer init: handle missing key first, then legacy int
        if today not in data[path]:
            data[path][today] = {"count": 0, "ip_ports": []}
        elif isinstance(data[path][today], int):
            old_count = data[path][today]
            data[path][today] = {"count": old_count, "ip_ports": []}
        
        # Always increment total visits (every hit counts)
        data[path][today]["count"] += 1
        
        # Only append IP if new (for unique tracking)
        if ip not in data[path][today]["ip_ports"]:
            data[path][today]["ip_ports"].append(ip)
        
        # Ensure directory exists before writing
        os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)
        
        with open(FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        return_dict["total_visits_today"] = data[path][today]["count"]
        return_dict["unique_ips"] = len(data[path][today]["ip_ports"])
        
        frappe.logger().info(f"record_visit SUCCESS: Wrote to {FILE_PATH}, result={return_dict}")
        return return_dict
    
    except Exception as e:
        frappe.logger().error(f"record_visit FAILED: {str(e)}")
        return_dict["error"] = str(e)
        return return_dict
# import frappe
# from datetime import datetime, timedelta

# def record_visit_console(page="/takari.html", ip_address="192.168.1.72", user_agent="console-agent"):
#     try:
#         recent_cutoff = datetime.now() - timedelta(minutes=5)
#         recent_visits = frappe.db.get_list('Visitor Log',
#             filters={
#                 'ip_address': ip_address,
#                 'creation': ['>', recent_cutoff]
#             },
#             fields=['name']
#         )
#         if recent_visits:
#             return {'message': 'Visit already recorded recently', 'status': 'skipped'}
        
#         doc = frappe.get_doc({
#             'doctype': 'Visitor Log',
#             'ip_address': ip_address,
#             'user_agent': user_agent,
#             'page': page
#         })
#         doc.insert(ignore_permissions=True)
#         frappe.db.commit()
#         return {'message': 'Visit recorded successfully', 'status': 'success'}
#     except Exception as e:
#         frappe.db.rollback()
#         return {'message': f'Error: {str(e)}', 'status': 'error'}

# # Record a visit
# result = record_visit_console(page="/takari.html")
# # print(result)

# # Get total visits
# total = frappe.db.count('Visitor Log')
# # print("Total visits:", total)
