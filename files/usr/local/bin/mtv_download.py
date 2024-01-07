#!/usr/bin/python3
# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# Mediathekview auf der Kommandozeile
#
# Methoden rund um den Download
#
# Author: Bernhard Bablok
# License: GPL3
#
# Website: https://github.com/bablokb/mtv_cli
#
# --------------------------------------------------------------------------

# --- System-Imports   -----------------------------------------------------

import os
import subprocess
import shlex
from subprocess import DEVNULL,STDOUT
import requests
from multiprocessing.pool import ThreadPool

# --- eigene Imports   ------------------------------------------------------

from mtv_msg    import Msg as Msg

# --- Download eines Films   -----------------------------------------------

def download_film(options,film):
  """Download eines einzelnen Films"""

  # Infos zusammensuchen
  _id = film._id
  size,url = film.get_url(options.config["QUALITAET"])
  film.thema = film.thema.replace('/','_')
  film.titel = film.titel.replace('/','_')
  ext        = url.split(".")[-1].lower()

  # Kommando bei Playlisten anpassen. Die Extension der gespeicherten Datei
  # wird auf mp4 geändert
  if ext.startswith('m3u'):
    cmd   = options.config["CMD_DOWNLOADS_M3U"]
    ext   = 'mp4'
    isM3U = True
  else:
    cmd = options.config["CMD_DOWNLOADS"]
    isM3U = False

    # make sure we always get best quality, options.config["QUALITAET"] will be ignored
    size,urlHD = film.get_url("HD")
    sizeHD = requests.get(urlHD, stream=True).headers['Content-length']
    
    size,urlSD = film.get_url("SD")
    sizeSD = requests.get(urlSD, stream=True).headers['Content-length']
    
    if int(sizeSD) > int(sizeHD):
      size = sizeSD
      url = urlSD
    else:
      size = sizeHD
      url = urlHD

  ziel = options.config["ZIEL_DOWNLOADS"].format(ext=ext, **film.asDict())
  cmd = cmd.format(ziel=ziel,url=url)

  # Zielverzeichnis erstellen
  ziel_dir = os.path.dirname(ziel)
  if not os.path.exists(ziel_dir):
    os.mkdir(ziel_dir)

  # Download ausführen
  options.filmDB.update_downloads(_id,'A')
  Msg.msg("INFO","Start Download (%s) %s" % (size,film.titel[0:50]))
  if isM3U:
    Msg.msg("DEBUG","Kommando: %s" % cmd)
    p = subprocess.Popen(cmd,shell=True,stdout=DEVNULL, stderr=STDOUT)
  else:
    Msg.msg("DEBUG","Kommando: %r" % shlex.split(cmd))
    p = subprocess.Popen(shlex.split(cmd),stdout=DEVNULL, stderr=STDOUT)
  p.wait()
  rc = p.returncode
  Msg.msg("INFO",
      "Ende  Download (%s) %s (Return-Code: %d)" % (size,film.titel[0:50],rc))
  if rc==0:
    options.filmDB.update_downloads(_id,'K')
    options.filmDB.save_recs(_id,ziel)
  else:
    options.filmDB.update_downloads(_id,'F')

  return rc

# --- Download aller Filme   -----------------------------------------------

def download_filme(options,status="'V','F','A'"):
  # Filme lesen
  filme = options.filmDB.read_downloads(ui=False,status=status)

  if not filme:
    Msg.msg("INFO","Keine vorgemerkten Filme vorhanden")
    return

  if options.config["NUM_DOWNLOADS"] == 1:
    # Spezialbehandlung (erleichtert Debugging)
    for film in filme:
      download_film(options,film)
  else:
    with ThreadPool(options.config["NUM_DOWNLOADS"]) as pool:
      for film in filme:
        pool.apply_async(download_film,(options,film))
      pool.close()
      pool.join()

  options.filmDB.save_status('_download')
