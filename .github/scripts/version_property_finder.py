import re
import sys
import xml.etree.ElementTree as ET


NS = {"m": "http://maven.apache.org/POM/4.0.0"}


# Retrieve the version tag name from a Maven property reference like ${foo.version}.
def get_version_tag(version_text):
    match = re.fullmatch(r"\$\{([^}]+)\}", version_text.strip())
    return match.group(1) if match else None


def get_text(element):
    return element.text.strip() if element is not None and element.text else None


def get_project_value(root, tag):
    value = get_text(root.find(f"./m:{tag}", NS))
    if value:
        return value
    return get_text(root.find(f"./m:parent/m:{tag}", NS))


def get_module_artifact_pairs(repo_dir):
    root = ET.parse(repo_dir + '/pom.xml').getroot()
    packaging = get_text(root.find("./m:packaging", NS)) or "jar"

    artifact_pairs = set()

    # If the root itself is a concrete artifact, include it.
    if packaging != "pom":
        group_id = get_project_value(root, "groupId")
        artifact_id = get_text(root.find("./m:artifactId", NS))
        if group_id and artifact_id:
            artifact_pairs.add((group_id, artifact_id))

    # Collect artifact pairs from child modules if present.
    modules = root.findall("./m:modules/m:module", NS)
    for module in modules:
        module_name = get_text(module)
        if not module_name:
            continue
        module_root = ET.parse(f"{repo_dir}/{module_name}/pom.xml").getroot()
        group_id = get_project_value(module_root, "groupId")
        artifact_id = get_text(module_root.find("./m:artifactId", NS))
        if group_id and artifact_id:
            artifact_pairs.add((group_id, artifact_id))

    # Fallback for single-module repos whose root POM is the artifact.
    if not artifact_pairs:
        group_id = get_project_value(root, "groupId")
        artifact_id = get_text(root.find("./m:artifactId", NS))
        if group_id and artifact_id:
            artifact_pairs.add((group_id, artifact_id))

    return artifact_pairs


def get_dependency_version_mapping(is_dir):
    is_root = ET.parse(is_dir + '/pom.xml').getroot()
    dependencies = is_root.findall(".//m:dependencies/m:dependency", NS)

    dependency_dict = {}
    for dependency in dependencies:
        group_id = get_text(dependency.find('./m:groupId', NS))
        artifact_id = get_text(dependency.find('./m:artifactId', NS))
        version = get_text(dependency.find('./m:version', NS))

        if group_id and artifact_id and version:
            dependency_dict[(group_id, artifact_id)] = version

    return dependency_dict


try:
    exit_code = "invalid"
    repo_dir = sys.argv[1]
    is_dir = sys.argv[2]

    repo_artifact_pairs = get_module_artifact_pairs(repo_dir)
    dependency_version_mapping = get_dependency_version_mapping(is_dir)

    matched_version_tags = set()
    for artifact_pair in repo_artifact_pairs:
        version_text = dependency_version_mapping.get(artifact_pair)
        if version_text:
            version_tag = get_version_tag(version_text)
            if version_tag:
                matched_version_tags.add(version_tag)

    # Only return a version property if all matched artifacts resolve to the same one.
    if len(matched_version_tags) == 1:
        exit_code = next(iter(matched_version_tags))
finally:
    sys.exit(exit_code)
