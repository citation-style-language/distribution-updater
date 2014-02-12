#!/usr/bin/python

from __future__ import print_function
import sys
import os
import re
import argparse
import fcntl
import subprocess
import dateutil.parser
import pytz

def git_cmd(root, params):
    return ["git", "-C", root] + params

def execute_subprocess(options, print_stdout=False):
    p = subprocess.Popen(options, stdout=subprocess.PIPE)
    output = p.communicate()
    if print_stdout and output[0]:
        print(output[0].rstrip())
    if p.returncode != 0:
        raise Exception("Error running process")
    return output[0]

def write_readme_md():
    text = """CSL Styles Distribution
======================

This repository is a copy of [citation-style-language/styles](https://github.com/citation-style-language/styles), refreshed on every commit, with each file's &lt;updated&gt; timestamp set to the file's last git commit time.

Licensing
---------
Please refer to https://github.com/citation-style-language/styles.
"""

    with open(os.path.join(DISTRIBUTION_STYLES_DIRECTORY, "README.md"), "w") as f:
        f.write(text)

def last_commit_hash():
    """ Returns the last commit of the ORIGINAL_STYLES_DIRECTORY. """
    return execute_subprocess(git_cmd(ORIGINAL_STYLES_DIRECTORY, [
        "log",
        "-n1",
        "--format=%H",
        ORIGINAL_STYLES_DIRECTORY
    ]))

def count_styles_git_index(directory):
    count = 0
    files = execute_subprocess(git_cmd(directory, ["ls-files"]))
    for filename in files.split("\n"):
        if filename.endswith('.csl'):
            count += 1
    return count

def get_file_commit_time(root, rel_file_path):
    string_date = execute_subprocess(git_cmd(root, [
        "log",
        "-n1",
        "--format=%ci",
        os.path.join(root, rel_file_path)
    ]))
    string_date = string_date.rstrip("\n")
    # Always store dates as UTC rather than the committer's TZ
    date = dateutil.parser.parse(string_date)
    return date.astimezone(pytz.timezone('UTC')).isoformat()

def process_files():
    print("Processing files")

    files_to_keep = []
    num_added = 0
    num_updated = 0
    num_skipped = 0

    try:
        os.mkdir(os.path.join(DISTRIBUTION_STYLES_DIRECTORY, "dependent"))
    except OSError:
        pass

    for root, dirs, files in os.walk(ORIGINAL_STYLES_DIRECTORY):
        for filename in files:
            # Skip directories other than root and 'dependent'
            if (root != ORIGINAL_STYLES_DIRECTORY and
                    root != os.path.join(ORIGINAL_STYLES_DIRECTORY, 'dependent')):
                continue

            # Skip non-CSL files
            if not filename.endswith('.csl'):
                continue

            orig_abs_path = os.path.join(root, filename)
            rel_path = os.path.relpath(orig_abs_path, ORIGINAL_STYLES_DIRECTORY)
            dist_abs_path = os.path.join(DISTRIBUTION_STYLES_DIRECTORY, rel_path)

            with open(orig_abs_path) as f:
                orig_style = f.read()
            try:
                with open(dist_abs_path) as f:
                    dist_style = f.read()
            except IOError:
                dist_style = False
                print("Adding {0}".format(rel_path))
                num_added += 1

            pattern = r'<updated>[^<]*</updated>'

            # If distribution file already exists, see if it differs from
            # original, ignoring the update time
            if dist_style:
                orig_style_clean = re.sub(pattern, '<updated></updated>', orig_style)
                dist_style_clean = re.sub(pattern, '<updated></updated>', dist_style)

                if orig_style_clean == dist_style_clean:
                    #print("Skipping {0}".format(rel_path))
                    files_to_keep.append(rel_path)
                    num_skipped += 1
                    continue

                print("Updating {0}".format(rel_path))
                num_updated += 1

            # Write the style to the distribution directory with the last
            # commit time as the updated timestamp
            updated = get_file_commit_time(ORIGINAL_STYLES_DIRECTORY, rel_path)
            dist_style = re.sub(pattern, '<updated>{0}</updated>'.format(updated), orig_style)
            with open(dist_abs_path, 'w') as f:
                f.write(dist_style)

            files_to_keep.append(rel_path)

    return {
        "files_to_keep": files_to_keep,
        "num_added": num_added,
        "num_updated": num_updated,
        "num_skipped": num_skipped
    }

def prune_distribution_files(files_to_keep):
    count = 0
    for root, dirs, files in os.walk(DISTRIBUTION_STYLES_DIRECTORY):
        for filename in files:
            # Skip non-CSL files
            if not filename.endswith(".csl"):
                continue
            abs_path = os.path.join(root, filename)
            rel_path = os.path.relpath(abs_path, DISTRIBUTION_STYLES_DIRECTORY)
            if rel_path in files_to_keep:
                continue
            print("Deleting {0}".format(rel_path))
            os.unlink(abs_path)
            count += 1
    return count

def push_changes(dry_run):
    write_readme_md()

    execute_subprocess(git_cmd(DISTRIBUTION_STYLES_DIRECTORY, ["add", "-A"]), True)

    execute_subprocess(git_cmd(DISTRIBUTION_STYLES_DIRECTORY, [
        "commit",
        "-a",
        "-m",
        "Synced up to https://github.com/citation-style-language/styles/commit/{0}".format(last_commit_hash())
    ]), True)

    original_styles_count = count_styles_git_index(ORIGINAL_STYLES_DIRECTORY)
    distribution_styles_count = count_styles_git_index(DISTRIBUTION_STYLES_DIRECTORY)

    print("Original styles: {0}".format(original_styles_count))
    print("Distribution styles: {0}".format(distribution_styles_count))

    if original_styles_count != distribution_styles_count:
        raise Exception("Style counts do not match!")

    if distribution_styles_count < 6000:
        raise Exception("Distribution repo has fewer than 6000 styles!")

    if dry_run:
        print("Dry run -- not pushing to distribution repo")
        return

    print("Pushing changes to distribution repo")
    execute_subprocess(git_cmd(DISTRIBUTION_STYLES_DIRECTORY, ["push"]), True)

def main(dry_run, commit):
    lock_file_path = "/tmp/csl-update.lock"
    lock_file = open(lock_file_path, "w")
    fcntl.flock(lock_file, fcntl.LOCK_EX)

    execute_subprocess(git_cmd(ORIGINAL_STYLES_DIRECTORY, ["checkout", "master"]), True)
    execute_subprocess(git_cmd(ORIGINAL_STYLES_DIRECTORY, ["pull"]), True)
    execute_subprocess(git_cmd(ORIGINAL_STYLES_DIRECTORY, ["checkout", commit]), True)

    execute_subprocess(git_cmd(DISTRIBUTION_STYLES_DIRECTORY, ["checkout", "master"]), True)
    execute_subprocess(git_cmd(DISTRIBUTION_STYLES_DIRECTORY, ["pull"]), True)

    result = process_files()
    num_deleted = prune_distribution_files(result["files_to_keep"])

    print("Added: {0}".format(result["num_added"]))
    print("Updated: {0}".format(result["num_updated"]))
    print("Skipped: {0}".format(result["num_skipped"]))
    print("Deleted: {0}".format(num_deleted))

    push_changes(dry_run)

    lock_file.close()
    os.unlink(lock_file_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Prepares and pushes style repository to be distributed.')
    parser.add_argument('--dry-run', action='store_true', help='Do everything except git push (default: %(default)s).', default=False)
    parser.add_argument('--commit', default='HEAD', help='Which commit to checkout from --original_styles_directory (default: %(default)s)')
    parser.add_argument('--original-styles-directory', required=True, help='Directory with a git checkout of https://github.com/citation-style-language/styles')
    parser.add_argument('--distribution-styles-directory', required=True, help='Directory with a git checkout of the destination directory')
    args = vars(parser.parse_args())

    ORIGINAL_STYLES_DIRECTORY = args['original_styles_directory']
    DISTRIBUTION_STYLES_DIRECTORY = args['distribution_styles_directory']

    main(args['dry_run'], args['commit'])
