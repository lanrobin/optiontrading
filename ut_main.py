import unittest
import sys

import HtmlTestRunner

def main():
    suite_test = unittest.TestSuite()
    suite_test.addTests([
        unittest.defaultTestLoader.discover(start_dir="./testcases", pattern="ut_*.py")
        ])

    generate_html = len(sys.argv) > 1 and sys.argv[1].startswith('html')
    if generate_html:
        runner = HtmlTestRunner.HTMLTestRunner(output = "testresult",report_title='UTReport')
        runner.run(suite_test)
    else:
        runner = unittest.TextTestRunner()
        runner.run(suite_test)

if __name__ == '__main__':
    main()