#! /usr/bin/env python
"""
    WSGI APP to convert wkhtmltopdf As a webservice

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import json
import tempfile
import os

from werkzeug.wsgi import wrap_file
from werkzeug.wrappers import Request, Response
from executor import execute


@Request.application
def application(request):
    """
    To use this application, the user must send a POST request with
    base64 or form encoded encoded HTML content and the wkhtmltopdf Options in
    request data, with keys 'base64_html' and 'options'.
    The application will return a response with the PDF file.
    """
    if request.method != 'POST':
        return

    request_is_json = request.content_type.endswith('json')

    with tempfile.NamedTemporaryFile(suffix='.html') as source_file:

        if request_is_json:
            # If a JSON payload is there, all data is in the payload
            payload = json.loads(request.data)
            source_file.write(payload['contents'].decode('base64'))
            # Load a list of files to do the merge
            pdf_files = payload.get('fichs', {})
            options = payload.get('options', {})
            # Load command exec file wkhtmltopdf or pdftk
            cmd = payload['cmd']
        elif request.files:
            # First check if any files were uploaded
            source_file.write(request.files['file'].read())
            # Load a list of files to do the merge
            pdf_files = request.files.getlist('fichs')
            # Load any options that may have been provided in options
            options = json.loads(request.form.get('options', '{}'))
            # Load command exec file wkhtmltopdf or pdftk
            cmd = request.files['cmd']

        source_file.flush()

        # Evaluate argument to run with subprocess
        args = ['wkhtmltopdf']
        if (cmd == 'pdftk'):
            args = ['pdftk']

        # Add Global Options
        if options:
            for option, value in options.items():
                args.append('--%s' % option)
                if value:
                    args.append('"%s"' % value)

        if pdf_files and (cmd == 'pdftk') :
            if request_is_json:
                for f, value in pdf_files.items():
                    sf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
                    sf.write(value.decode('base64'))
                    sf.close()
                    # Add source file name
                    args += [sf.name]

        # Add source file name and output file name
        file_name = source_file.name
        args += [file_name, file_name + ".pdf"]

        # Execute the command using executor
        execute(' '.join(args))

        file_raw = open(file_name + '.pdf');

        if os.path.isfile(file_name + ".pdf"):
            os.remove(file_name + ".pdf")
        else:    ## Show an error ##
            file_name_msg = file_name + ".pdf"
            print("Error: %s file not found" % file_name_msg)

        return Response(
            wrap_file(request.environ, file_raw),
            mimetype='application/pdf',
        )


if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple(
        '127.0.0.1', 5000, application, use_debugger=True, use_reloader=True
    )
