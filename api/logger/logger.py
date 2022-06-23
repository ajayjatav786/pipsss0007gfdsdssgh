import logging

def get_logger(name):
    
    console_info_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] <%(module)s> - %(message)s', datefmt='%Y-%m-%d %H:%M:%S %z')
    console_err_formatter = logging.Formatter('[%(asctime)s]~[%(levelname)s]~%(message)s~module:%(module)s~function:%(module)s', datefmt='%y-%m-%d %H:%M:%S %z')
        
    #file_handler = logging.FileHandler("logfile.log")
    #file_handler.setLevel(logging.WARN)
    #file_handler.setFormatter(file_formatter)
    
    console_info_handler = logging.StreamHandler()
    console_info_handler.setLevel(logging.INFO)
    console_info_handler.setFormatter(console_info_formatter)
    
    console_err_handler = logging.StreamHandler()
    console_err_handler.setLevel(logging.ERROR)
    console_err_handler.setFormatter(console_err_formatter)
       
    
    logger = logging.getLogger(name)
    #logger.addHandler(file_handler)
    logger.addHandler(console_info_handler)
    logger.addHandler(console_err_handler)
    logger.setLevel(logging.INFO)
    
    return logger