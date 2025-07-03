{
    'name': 'Petty Cash Management',
    'category': 'Accounting/Finance', 
    'version': '18.0.1.0.0',  
    'summary': 'Manage petty cash transactions and reports',
    'description': "petty_cash_management_module",
    'author': 'ewis',      
    
    
    'depends': ['base', 'account'],
    'external_dependencies': {
      'python': ['pytesseract','Pillow','pdf2image'],
      'bin': ['tesseract'], 
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',  

    
    'data': [
        
        
        #security
        'security/ir.model.access.csv',
        #data
        'data/sequence_data.xml',
        #wizard
        'wizard/cash_denomination_wizard_view.xml',
        #views
        'views/petty_cash_request_views.xml',
        'views/petty_cash_category_views.xml',
        'views/petty_cash_menu.xml',
        
    ], 
}