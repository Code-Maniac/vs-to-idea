#!/usr/bin/env python3

import os
import sys
import re
import json
import xml.etree.cElementTree as ET
import lxml.etree as etree  # to prettify
import multiprocessing

# record the generation dirs so that we can make new ones
used_gen_dirs = []


def main():
    # first check preconditions
    if len(sys.argv) < 2:
        print("Not enough args")
        exit(1)

    project_dir = sys.argv[1]
    if not os.path.exists(project_dir):
        print("Folder does not exist")
        exit(1)

    idea_dir = project_dir + "/.idea"
    if os.path.exists(idea_dir):
        print("Project already contains .idea folder")
        exit(1)

    cmake_path = project_dir + "/CMakeSettings.json"
    if not os.path.exists(cmake_path):
        print("No CMakeSettings.json found in project dir")
        exit(1)

    # create the .idea dir and write the misc.xml file
    os.mkdir(idea_dir)
    # with open(idea_dir + "/misc.xml", "w") as f:
    #     f.write('<?xml version="1.0" encoding="UTF-8"?>\n<project version="4">\n  <component name="CMakeWorkspace" PROJECT_DIR="$ProjectFileDir$" />\n</project>')

    print(cmake_path)
    if create_cmake(cmake_path, idea_dir + "/cmake.xml"):
        exit(0)
    else:
        exit(1)


def create_cmake(input_path, output_path):
    configs = []
    with open(input_path) as f:
        json_str = f.read()
        json_str = remove_comments(json_str)
        data = json.loads(json_str)

    # for each configuration in the data. Check that it's a Visual Studio
    # config and if it is then add a .idea version of it to the configs as
    # a subelement
    # Discard not Visual Studio configs for now - add this when we add support
    # for 64 bit cygwin to SDKC
    for jconfig in data["configurations"]:
        # unpack the data
        name = jconfig["name"]
        generator = jconfig["generator"]
        configurationType = jconfig["configurationType"]
        # inheritEnvironments = jconfig["inheritEnvironments"]
        buildRoot = jconfig["buildRoot"]
        # installRoot = jconfig["installRoot"]
        cmakeCommandArgs = jconfig["cmakeCommandArgs"]
        # buildCommandArgs = jconfig["buildCommandArgs"]
        # ctestCommandArgs = jconfig["ctestCommandArgs"]

        if "Visual Studio" in generator:
            # write to the xml
            configs.append(get_config_xml(name, configurationType,
                           buildRoot, cmakeCommandArgs))

    return write_xml_doc(configs, output_path)


def remove_comments(text):
    def replacer(match):
        s = match.group(0)
        if s.startswith('/'):
            return " "  # note: a space and not an empty string
        else:
            return s
    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE
    )
    return re.sub(pattern, replacer, text)


# write the xml document to the path
# given an array of configuration SubElements to add to the configurations
def write_xml_doc(configs, output_path):
    root = ET.Element("project")
    root.set("version", "4")

    component = ET.SubElement(root, "component")
    component.set("name", "CMakeSharedSettings")

    configurations = ET.SubElement(component, "configurations")
    for item in configs:
        configurations.append(item)

    indent(root)

    # print(ET.tostring(root, encoding="utf8", method="xml"))
    tree = ET.ElementTree(root)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)

    return True


# get a new configuration subelement for the given data
def get_config_xml(name, configurationType,
                   buildRoot, cmakeCommandArgs):
    # make the build root different from the vs build root so that they can
    # exist seperately if needed
    buildRoot += "-clion"
    # remove initial "${thisFileDir}\\" from buildRoot
    buildRoot = buildRoot.replace("${thisFileDir}\\", "")
    # change remaining \\ to /
    buildRoot = buildRoot.replace("\\", "/")

    if buildRoot in used_gen_dirs:
        buildRoot += "_" + name

    # just assume this as far as it will go
    used_gen_dirs.append(buildRoot)

    if "2017" in name:
        toolchain_year = "2017"
    else:
        toolchain_year = "2019"

    config = ET.Element("configuration")
    config.set("PROFILE_NAME", name)
    config.set("ENABLED", "true")
    config.set("GENERATION_DIR", buildRoot)
    config.set("CONFIG_NAME", configurationType)
    config.set("TOOLCHAIN_NAME", f"Visual Studio {toolchain_year}")
    config.set("GENERATION_OPTIONS", cmakeCommandArgs)

    if multiprocessing.cpu_count() > 1:
        config.set("BUILD_OPTIONS", f"-j {multiprocessing.cpu_count() - 1}")

    # add_gen_env = ET.SubElement(config, "ADDITIONAL_GENERATION_ENVIRONMENT")
    # envs = ET.SubElement(add_gen_env, "envs")
    #
    # for item in cmakeCommandArgs.split():
    #     env = ET.SubElement(envs, "env")
    #     pair = item.split("=")
    #     env.set("name", pair[0])
    #     env.set("value", pair[1])

    return config


def indent(elem, level=0):
    i = "\n" + level*"  "
    j = "\n" + (level-1)*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for subelem in elem:
            indent(subelem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = j
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = j
    return elem


if __name__ == "__main__":
    main()
