# xml_parser.py
from lxml import etree
import re 

def load_xml_from_file(file_path):
    """Loads and parses an XML file using lxml."""
    try:
        parser = etree.XMLParser(encoding='utf-8')
        tree = etree.parse(file_path, parser)
        return tree.getroot()
    except etree.XMLSyntaxError as e:
        print(f"Error parsing XML file: {e}")
        try:
            print("Retrying XML parsing without explicit encoding...")
            tree = etree.parse(file_path)
            return tree.getroot()
        except Exception as e2:
            print(f"Retry failed: {e2}")
            return None
    except FileNotFoundError:
        print(f"Error: XML file not found at {file_path}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading XML: {e}")
        return None

def extract_build_basics(root):
    """Extracts basic build information: Class, Ascendancy, Level, Main Skill DPS."""
    if root is None: return {}
    build_info = {}
    try:
        build_element = root.find("Build")
        if build_element is not None:
            build_info["className"] = build_element.get("className")
            build_info["ascendClassName"] = build_element.get("ascendClassName")
            build_info["level"] = build_element.get("level")
            build_info["mainSocketGroup"] = build_element.get("mainSocketGroup")
            dps_stat = build_element.find("PlayerStat[@stat='TotalDPS']")
            if dps_stat is not None: build_info["totalDPS"] = dps_stat.get("value")
            else:
                combined_dps_stat = build_element.find("PlayerStat[@stat='CombinedDPS']")
                if combined_dps_stat is not None: build_info["totalDPS_Combined"] = combined_dps_stat.get("value")
                else: build_info["totalDPS"] = "N/A"
        else:
            print("Error: <Build> element not found in XML.")
            return {}
    except Exception as e: print(f"Error extracting build basics: {e}")
    return build_info

def extract_character_stats(root):
    """Extracts core character stats like Life, Mana, ES, Resistances."""
    if root is None: return {}
    stats = {}
    build_element = root.find("Build")
    if build_element is None:
        print("Error: <Build> element not found for character stats.")
        return stats
    stat_map = {
        "Life": "Life", "Mana": "Mana", "EnergyShield": "EnergyShield", "Armour": "Armour",
        "Evasion": "Evasion", "FireResist": "FireResist", "ColdResist": "ColdResist",
        "LightningResist": "LightningResist", "ChaosResist": "ChaosResist",
        "EffectiveHP": "TotalEHP", "CritChance": "CritChance", "CritMultiplier": "CritMultiplier",
        "HitChance": "HitChance", "AttackSpeed": "Speed", "ManaRegen": "ManaRegenRecovery",
        "LifeRegen": "LifeRegenRecovery", "SpellSuppression": "EffectiveSpellSuppressionChance"
    }
    for display_name, xml_stat_name in stat_map.items():
        stat_element = build_element.find(f"PlayerStat[@stat='{xml_stat_name}']")
        stats[display_name] = stat_element.get("value") if stat_element is not None else "N/A"
    return stats

def extract_skills_data(root):
    """Extracts skill setups including main skill name, gems, levels, and quality."""
    if root is None: return {}
    skills_data = {"all_skills": [], "main_skill_name": "N/A"}
    skills_element = root.find("Skills")
    if skills_element is None: 
        print("Error: <Skills> element not found for skill data.")
        return skills_data
    
    for skill_set in skills_element.findall("SkillSet"):
        for skill_node in skill_set.findall("Skill"):
            skill_info = {
                "label": skill_node.get("label", ""),
                "enabled": skill_node.get("enabled") == "true",
                "is_main": skill_node.get("mainActiveSkill") == "1",
                "source": skill_node.get("source", "Socketed"),
                "gems": []
            }
            if skill_info["is_main"]:
                first_gem = skill_node.find("Gem")
                if first_gem is not None:
                    skills_data["main_skill_name"] = first_gem.get("nameSpec", "Unknown Main Skill")
            for gem_node in skill_node.findall("Gem"):
                gem_info = {
                    "name": gem_node.get("nameSpec"), "level": gem_node.get("level"),
                    "quality": gem_node.get("quality"), "skillId": gem_node.get("skillId"),
                    "enabled": gem_node.get("enabled") == "true"
                }
                skill_info["gems"].append(gem_info)
            if skill_info["gems"]: skills_data["all_skills"].append(skill_info)
    return skills_data

def extract_items_data(root):
    """Extracts equipped items, their rarity, name, base type, and mods."""
    if root is None: return {}
    items_data = {"equipped_items": []}
    items_element = root.find("Items")
    tree_element = root.find("Tree") 
    
    if items_element is None:
        print("Error: <Items> element not found.")
        return items_data

    jewel_socket_map = {}
    if tree_element is not None:
        spec_elements = tree_element.findall("Spec") 
        for spec_node in spec_elements: 
            sockets_node = spec_node.find("Sockets")
            if sockets_node is not None:
                for socket_node in sockets_node.findall("Socket"):
                    item_id = socket_node.get("itemId")
                    node_id = socket_node.get("nodeId")
                    if item_id and node_id:
                        jewel_socket_map[item_id] = f"Jewel Socket (Tree Node {node_id})"

    for item_node in items_element.findall("Item"):
        item_id = item_node.get("id")
        full_text_content = item_node.text
        if not full_text_content: continue
        lines = [line.strip() for line in full_text_content.strip().split('\n') if line.strip()]
        item_info = {
            "id": item_id, "slot": "Unknown Slot", "name": "Unknown Item",
            "base_type": "Unknown Base", "rarity": "Unknown", "mods": [],
            "raw_text_lines": lines 
        }
        item_set_element = items_element.find("ItemSet")
        if item_set_element is not None:
            slot_element = item_set_element.find(f"Slot[@itemId='{item_id}']")
            if slot_element is not None: item_info["slot"] = slot_element.get("name")
        if item_info["slot"] == "Unknown Slot" and item_id in jewel_socket_map:
            item_info["slot"] = jewel_socket_map[item_id]
        line_idx = 0
        if lines:
            if lines[line_idx].startswith("Rarity:"):
                item_info["rarity"] = lines[line_idx].split(":", 1)[1].strip()
                line_idx += 1
            if line_idx < len(lines):
                potential_name = lines[line_idx]
                if item_info["rarity"] in ["RARE", "UNIQUE"]:
                    item_info["name"] = potential_name
                    line_idx += 1
                    if line_idx < len(lines) and not lines[line_idx].lower().startswith(("unique id:", "item level:", "implicits:", "radius:")):
                        is_jewel_base = "jewel" in item_info["slot"].lower() or any(jb in lines[line_idx].lower() for jb in ["emerald", "sapphire", "ruby", "viridian", "cobalt", "crimson", "prism"])
                        if is_jewel_base or not any(kw in lines[line_idx] for kw in ["%", "adds", "to ", "+", "leech", "regenerate"]):
                             item_info["base_type"] = lines[line_idx]
                             line_idx += 1
                elif item_info["rarity"] in ["MAGIC", "NORMAL"]:
                    item_info["name"] = potential_name 
                    line_idx += 1 
                else: 
                    item_info["name"] = potential_name
                    line_idx +=1
            non_mod_prefixes = ("unique id:", "item level:", "quality:", "levelreq:", "sockets:", "rune:", "implicits: 0", "implicits: 1", "implicits: 2", "radius:")
            base_stat_prefixes = ("evasion:", "energy shield:", "armour:", "spirit:")
            current_mods = []
            for i in range(line_idx, len(lines)):
                line_lower = lines[i].lower()
                is_base_stat_line = any(line_lower.startswith(bp) for bp in base_stat_prefixes) and item_info["rarity"] != "UNIQUE"
                if not line_lower.startswith(non_mod_prefixes) and not is_base_stat_line \
                   and not (item_info["rarity"] != "UNIQUE" and lines[i] == item_info["base_type"]) :
                    if any(keyword in lines[i] for keyword in ["%", "adds", " to ", "+", "leech", "regenerate", "penetrates", "increased", "reduced", "more", "less", "gain", "grants skill", "allocates"]) or item_info["rarity"] in ["RARE", "UNIQUE"]:
                         current_mods.append(lines[i])
            item_info["mods"] = current_mods
        items_data["equipped_items"].append(item_info)
    return items_data

def extract_passive_tree_data(root):
    """Extracts active passive tree notables."""
    if root is None: return {}
    tree_data = {"notables": [], "keystones": [], "masteries": [], "url": "N/A", "allocated_node_ids": [], "mastery_effects_raw": ""}
    tree_element = root.find("Tree")
    if tree_element is None:
        print("Error: <Tree> element not found.")
        return tree_data
    spec_element = tree_element.find("Spec") 
    if spec_element is not None:
        tree_data["url"] = spec_element.findtext("URL", default="N/A")
        nodes_str = spec_element.get("nodes", "")
        if nodes_str: tree_data["allocated_node_ids"] = nodes_str.split(',')
        tree_data["mastery_effects_raw"] = spec_element.get("masteryEffects", "")
    return tree_data

def format_data_for_llm(build_basics, char_stats, skills_xml_data, items_xml_data, tree_data, all_scraped_details=None):
    """Formats all extracted data into a single string for the LLM."""
    output = []
    output.append("### Path of Exile 2 Build Analysis Data (from PoB XML) ###")
    
    output.append("\n--- BUILD BASICS (from PoB XML) ---")
    for key, value in build_basics.items():
        key_formatted = key.replace('_', ' ').title()
        if "Totaldps Combined" in key_formatted : key_formatted = "Total DPS (Combined - PoB)"
        elif "Totaldps" in key_formatted : key_formatted = "Total DPS (Main Skill - PoB)"
        output.append(f"{key_formatted}: {value}")

    main_skill_name_from_xml = skills_xml_data.get('main_skill_name', 'N/A')
    output.append("\n--- CHARACTER STATS (Overall & for Main Skill: {}) ---".format(main_skill_name_from_xml))
    for key, value in char_stats.items():
        output.append(f"{key.replace('_', ' ').title()}: {value}")

    output.append("\n--- SKILL SETUPS (from PoB XML) ---")
    output.append(f"Main Skill Name (identified in PoB): {main_skill_name_from_xml}")
    for i, skill_group in enumerate(skills_xml_data.get("all_skills", [])):
        if skill_group["enabled"] and skill_group["gems"]:
            main_indicator = " (MAIN SKILL as per PoB)" if skill_group['is_main'] else ""
            source_info = f"(Source: {skill_group['source']})" if skill_group['source'] else ""
            output.append(f"\n  Skill Group {i+1}{main_indicator} {source_info}:")
            for gem in skill_group["gems"]:
                if gem["enabled"]:
                    gem_name = gem.get('name') if gem.get('name') else "Unnamed Skill/Effect"
                    output.append(f"    - {gem_name} (Lvl {gem.get('level','N/A')} Q{gem.get('quality','N/A')})")

    output.append("\n--- EQUIPPED ITEMS (from PoB XML) ---")
    for item in items_xml_data.get("equipped_items", []):
        output.append(f"\n  Slot: {item['slot']}")
        output.append(f"    Name: {item['name']}, Base: {item['base_type']}, Rarity: {item['rarity']}")
        if item['mods']:
            output.append(f"    Mods ({len(item['mods'])}):")
            for mod_line in item['mods']: 
                output.append(f"      - {mod_line}")
        else:
            output.append("    Mods: None")

    output.append("\n--- PASSIVE TREE (from PoB XML) ---")
    output.append(f"Tree URL: {tree_data.get('url')}")
    output.append(f"Allocated Node IDs (Count): {len(tree_data.get('allocated_node_ids', []))}")
    if tree_data.get('mastery_effects_raw') and tree_data.get('mastery_effects_raw') != "":
        output.append(f"Mastery Effects Raw: {tree_data.get('mastery_effects_raw')}")
    
    if all_scraped_details:
        if all_scraped_details.get("skills"):
            output.append("\n\n### DETAILED SKILL INFORMATION (Scraped from poe2db.tw) ###")
            for skill_details in all_scraped_details["skills"]:
                if skill_details.get("name", "N/A") == "N/A": continue
                output.append(f"\n--- Skill: {skill_details.get('name')} ---")
                output.append(f"  Source URL: {skill_details.get('source_url', 'N/A')}")
                output.append(f"  Primary Tag: {skill_details.get('primary_tag', 'N/A')}")
                if skill_details.get('secondary_tags'):
                    output.append(f"  Secondary Tags: {', '.join(skill_details['secondary_tags'])}")
                
                if skill_details.get("stats_properties"):
                    output.append("  Key Stats/Properties:")
                    for prop in skill_details["stats_properties"]: output.append(f"    - {prop}")
                if skill_details.get("requirements", "N/A") != "N/A":
                    output.append(f"  Requirements: {skill_details['requirements']}")

                description_text = skill_details.get('description', 'N/A')
                indented_description = description_text.replace(chr(10), chr(10) + "    ") 
                output.append(f"  Description:\n    {indented_description}")

                for effect_type_key, effect_type_name in [
                    ('spear_effects', "Spear Specific Effects"), 
                    ('lightning_bolts_stats', "Lightning Bolts Specific Stats/Effects"),
                ]:
                    if skill_details.get(effect_type_key):
                        output.append(f"  {effect_type_name}:")
                        for effect in skill_details[effect_type_key]: output.append(f"    - {effect}")
                
                if skill_details.get('quality_effects_heading', "N/A") != "N/A":
                    output.append(f"  {skill_details['quality_effects_heading']}:")
                    for q_mod in skill_details.get('quality_mods', []): output.append(f"    - {q_mod}")

                for table_key, table_name in [
                    ('level_scaling_table_text', "Level Scaling"),
                    ('attribute_table_text', "Attributes/Internal Data")
                ]:
                    if skill_details.get(table_key, "N/A") != "N/A":
                        output.append(f"\n  {table_name}:\n{skill_details[table_key]}") 
                output.append("--- End of Skill: {} ---".format(skill_details.get('name')))

        if all_scraped_details.get("items"):
            output.append("\n\n### DETAILED UNIQUE ITEM INFORMATION (Scraped from poe2db.tw) ###")
            for item_details in all_scraped_details["items"]:
                if item_details.get("name", "N/A") == "N/A": continue
                output.append(f"\n--- Unique Item: {item_details.get('name')} ---")
                output.append(f"  Source URL: {item_details.get('source_url', 'N/A')}")
                output.append(f"  Primary Tag/Type (Base Type): {item_details.get('primary_tag', 'N/A')}") 
                
                if item_details.get("stats_properties"): 
                    output.append("  Key Stats/Properties (e.g. LevelReq):")
                    for prop in item_details["stats_properties"]: output.append(f"    - {prop}")
                
                item_description_text = item_details.get('description', 'N/A') 
                indented_item_description = item_description_text.replace(chr(10), chr(10) + "    ")
                if item_description_text and item_description_text != "N/A": 
                    output.append(f"  Description/Flavor Text:\n    {indented_item_description}")
                
                if item_details.get('item_implicits'):
                    output.append("  Implicit Modifiers:")
                    for implicits in item_details['item_implicits']: output.append(f"    - {implicits}")
                if item_details.get('item_explicits'):
                    output.append("  Explicit Modifiers (Unique Properties):")
                    for explicits in item_details['item_explicits']: output.append(f"    - {explicits}")
                
                if item_details.get('attribute_table_text', "N/A") != "N/A": # Check if item has attribute table
                    output.append(f"\n  Attributes/Internal Data (from poe2db):\n{item_details['attribute_table_text']}")

                output.append("--- End of Unique Item: {} ---".format(item_details.get('name')))

    output.append("\n\n### END OF ALL BUILD DATA ###")
    return "\n".join(output)

if __name__ == "__main__":
    print(f"xml_parser.py executed as main. To test functions, call them directly or run main.py to see full integration.")