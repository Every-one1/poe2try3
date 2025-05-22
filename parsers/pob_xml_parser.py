# xml_parser.py
from lxml import etree
import re # For more advanced string manipulation if needed

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
    build_element = root.find("Build")
    if skills_element is None or build_element is None:
        print("Error: <Skills> or <Build> element not found for skill data.")
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
    tree_element = root.find("Tree") # For jewel socket mapping
    
    if items_element is None:
        print("Error: <Items> element not found.")
        return items_data

    # Pre-build a map of itemId to jewel socket nodeId for easier lookup
    jewel_socket_map = {}
    if tree_element is not None:
        for spec_node in tree_element.findall("Spec"): # Usually only one Spec
            for socket_node in spec_node.find("Sockets").findall("Socket"):
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
            "id": item_id,
            "slot": "Unknown Slot",
            "name": "Unknown Item",
            "base_type": "Unknown Base",
            "rarity": "Unknown",
            "mods": [],
            "raw_text_lines": lines # Store raw lines for debugging/further parsing
        }

        # Attempt to find slots from ItemSet first
        item_set_element = items_element.find("ItemSet")
        if item_set_element is not None:
            slot_element = item_set_element.find(f"Slot[@itemId='{item_id}']")
            if slot_element is not None:
                item_info["slot"] = slot_element.get("name")
        
        # If slot is still unknown, check if it's a jewel from tree sockets
        if item_info["slot"] == "Unknown Slot" and item_id in jewel_socket_map:
            item_info["slot"] = jewel_socket_map[item_id]
            # For jewels, the PoB text format is different.
            # Line 0: Rarity: RARE
            # Line 1: Jewel Name (e.g., Blight Glimmer)
            # Line 2: Jewel Base Type (e.g., Emerald)
            # Then mods.

        line_idx = 0
        if lines:
            # Parse Rarity
            if lines[line_idx].startswith("Rarity:"):
                item_info["rarity"] = lines[line_idx].split(":", 1)[1].strip()
                line_idx += 1
            
            # Parse Name and Base Type (this is heuristic)
            if line_idx < len(lines):
                potential_name = lines[line_idx]
                if item_info["rarity"] in ["RARE", "UNIQUE"]:
                    item_info["name"] = potential_name
                    line_idx += 1
                    if line_idx < len(lines) and not lines[line_idx].lower().startswith("unique id:") and not lines[line_idx].lower().startswith("item level:") and not lines[line_idx].lower().startswith("implicits:") and not lines[line_idx].lower().startswith("radius:") : # Basic check if next line is a base type
                        # A better check would be against a list of known base types or if it contains certain keywords
                        if item_info["slot"] == "Jewel Socket" or "Jewel" in item_info["slot"] or "Emerald" in lines[line_idx] or "Sapphire" in lines[line_idx] or "Ruby" in lines[line_idx] or "Viridian" in lines[line_idx]: # Heuristic for jewels
                             item_info["base_type"] = lines[line_idx]
                             line_idx +=1
                        elif not any(kw in lines[line_idx] for kw in ["%", "Adds", "to ", "+", "Leech", "Regenerate"]): # if it doesn't look like a mod
                             item_info["base_type"] = lines[line_idx]
                             line_idx += 1
                elif item_info["rarity"] in ["MAGIC", "NORMAL"]:
                    # For magic/normal, the name often includes the base type
                    item_info["name"] = potential_name # This will be like "Effervescent Ultimate Life Flask of the Continuous"
                    # We'd need a list of base types to extract it accurately.
                    # For now, leave base_type as "Unknown Base" or try a heuristic
                    # This part is complex and might require a base type database.
                    # Example: "Ultimate Life Flask" is the base
                    line_idx += 1 
                else: # Could be a currency or other item type
                    item_info["name"] = potential_name
                    line_idx +=1
            
            # The rest are potential mods, implicits, or other info
            # We need to be more selective about what we call a "mod"
            # Filter out common non-mod lines:
            non_mod_prefixes = (
                "unique id:", "item level:", "quality:", "levelreq:", "sockets:", "rune:", 
                "implicits: 0", "implicits: 1", "implicits: 2", # Handle implicits separately later
                "radius:", "evasion:", "energy shield:", "armour:", "spirit:" # These are base stats, not explicit mods
            )
            # Also filter out lines that are likely just base types if we misidentified earlier
            known_base_types_for_filtering = ["emerald", "sapphire", "ruby", "viridian", # Jewel bases
                                              "shrine sceptre", "swift bracers", "vile robe", # etc.
                                             ]


            current_mods = []
            for i in range(line_idx, len(lines)):
                line_lower = lines[i].lower()
                is_base_stat_line = False
                for prefix in ["evasion:", "energy shield:", "armour:", "spirit:"]:
                    if line_lower.startswith(prefix) and item_info["rarity"] != "UNIQUE": # Uniques might have these as flavor text
                        is_base_stat_line = True
                        break
                
                if not line_lower.startswith(non_mod_prefixes) and not is_base_stat_line \
                   and not (item_info["rarity"] != "UNIQUE" and lines[i] == item_info["base_type"]) : # Don't add base type as a mod
                    # A very simple check: if it contains '%' or 'Adds' or '+' or 'to ' (with space)
                    # or specific keywords like "Leech", "Regenerate", "Penetrates"
                    # This helps filter out lines that are just item type descriptions for non-rares/uniques
                    if any(keyword in lines[i] for keyword in ["%", "Adds", " to ", "+", "Leech", "Regenerate", "Penetrates", "increased", "reduced", "more", "less", "Gain", "Grants Skill", "Allocates"]) or item_info["rarity"] in ["RARE", "UNIQUE"]:
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


if __name__ == "__main__":
    sample_xml_file = "sample_build.xml" 
    root_element = load_xml_from_file(sample_xml_file)

    if root_element is not None:
        print("--- Build Basics ---")
        basics = extract_build_basics(root_element)
        for key, value in basics.items(): print(f"{key}: {value}")

        print("\n--- Character Stats ---")
        char_stats = extract_character_stats(root_element)
        for key, value in char_stats.items(): print(f"{key}: {value}")

        print("\n--- Skills Data ---")
        skills = extract_skills_data(root_element)
        print(f"Main Skill Name (guess): {skills.get('main_skill_name', 'N/A')}")
        for i, skill_group in enumerate(skills.get("all_skills", [])):
            if skill_group["enabled"] and skill_group["gems"]:
                is_main_indicator = "(MAIN)" if skill_group['is_main'] else ""
                print(f"  Skill Group {i+1} {is_main_indicator} (Enabled: {skill_group['enabled']}, Source: {skill_group['source']}):")
                for gem in skill_group["gems"]:
                    if gem["enabled"]: print(f"    - {gem['name']} (Lvl {gem['level']} Q{gem['quality']})")
        
        print("\n--- Items Data ---")
        items_result = extract_items_data(root_element) # Corrected variable name
        for item in items_result.get("equipped_items", []):
            print(f"  Slot: {item['slot']}")
            print(f"    Name: {item['name']}, Base: {item['base_type']}, Rarity: {item['rarity']}")
            if item['mods']:
                print(f"    Mods ({len(item['mods'])}):")
                for mod_line in item['mods'][:5]: # Print first 5 mods
                    print(f"      - {mod_line}")
            # For debugging item parsing:
            # print("    Raw Lines:")
            # for raw_line in item['raw_text_lines']:
            #     print(f"      RAW: {raw_line}")


        print("\n--- Passive Tree Data ---")
        tree = extract_passive_tree_data(root_element)
        print(f"Tree URL: {tree.get('url')}")
        print(f"Allocated Node IDs (count): {len(tree.get('allocated_node_ids', []))}")
        if tree.get('mastery_effects_raw'): print(f"Mastery Effects Raw: {tree.get('mastery_effects_raw')}")
    else:
        print("Failed to parse XML.")

def format_data_for_llm(build_basics, char_stats, skills_data, items_data, tree_data):
    """Formats all extracted data into a single string for the LLM."""
    output = []

    output.append("### Path of Exile 2 Build Analysis Data ###")
    
    output.append("\n--- BUILD BASICS ---")
    for key, value in build_basics.items():
        output.append(f"{key.replace('_', ' ').title()}: {value}")

    output.append("\n--- CHARACTER STATS (Main Skill: {}) ---".format(skills_data.get('main_skill_name', 'N/A')))
    for key, value in char_stats.items():
        output.append(f"{key.replace('_', ' ').title()}: {value}")

    output.append("\n--- SKILL SETUPS ---")
    output.append(f"Main Skill Name: {skills_data.get('main_skill_name', 'N/A')}")
    for i, skill_group in enumerate(skills_data.get("all_skills", [])):
        if skill_group["enabled"] and skill_group["gems"]:
            main_indicator = " (MAIN SKILL)" if skill_group['is_main'] else ""
            output.append(f"\n  Skill Group {i+1}{main_indicator} (Source: {skill_group['source']}):")
            for gem in skill_group["gems"]:
                if gem["enabled"]:
                    output.append(f"    - {gem['name']} (Lvl {gem['level']} Q{gem['quality']})")

    output.append("\n--- EQUIPPED ITEMS ---")
    for item in items_data.get("equipped_items", []):
        output.append(f"\n  Slot: {item['slot']}")
        output.append(f"    Name: {item['name']}, Base: {item['base_type']}, Rarity: {item['rarity']}")
        if item['mods']:
            output.append(f"    Mods ({len(item['mods'])}):")
            for mod_line in item['mods']: # Send all mods now
                output.append(f"      - {mod_line}")
        # else:
        #     output.append("    Mods: None") # Or skip if no mods

    output.append("\n--- PASSIVE TREE ---")
    output.append(f"Tree URL: {tree_data.get('url')}")
    output.append(f"Allocated Node IDs (Count): {len(tree_data.get('allocated_node_ids', []))}")
    # Optional: send a few node IDs if the list is very long and LLM context is an issue
    # output.append(f"Allocated Node IDs (First 20): {tree_data.get('allocated_node_ids', [])[:20]}") 
    if tree_data.get('mastery_effects_raw'):
        output.append(f"Mastery Effects Raw: {tree_data.get('mastery_effects_raw')}")
    
    output.append("\n### END OF BUILD DATA ###")
    return "\n".join(output)

# Update the __main__ block in xml_parser.py to test this new function:
if __name__ == "__main__":
    sample_xml_file = "sample_build.xml" 
    root_element = load_xml_from_file(sample_xml_file)

    if root_element is not None:
        basics = extract_build_basics(root_element)
        char_stats = extract_character_stats(root_element)
        skills = extract_skills_data(root_element)
        items_result = extract_items_data(root_element)
        tree = extract_passive_tree_data(root_element)

        # --- Test the new formatter ---
        llm_input_string = format_data_for_llm(basics, char_stats, skills, items_result, tree)
        print("\n\n--- DATA FORMATTED FOR LLM ---")
        print(llm_input_string)
        # --- End test ---
    else:
        print("Failed to parse XML.")