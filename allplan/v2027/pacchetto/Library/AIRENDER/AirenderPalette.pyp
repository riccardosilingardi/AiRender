<?xml version='1.0' encoding='UTF-8'?>
<!-- Generato da allplan/v2027/scrivi_palette_pyp.py: non modificare a mano. -->
<Element xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd">
<Script>
<Name>riccardo_silingardi\airender\AirenderPalette.py</Name>
<Title>AIRENDER</Title>
<Version>1.0</Version>
</Script>
<Page>
<Name>Pagina</Name>
<Text>AIRENDER</Text>
<Parameters>
<Parameter>
<Name>ImmaginiDaScript</Name>
<Value>0</Value>
<ValueType>Integer</ValueType>
<Visible>False</Visible>
</Parameter>
<Parameter>
<Name>InCorso</Name>
<Value>0</Value>
<ValueType>Integer</ValueType>
<Visible>False</Visible>
</Parameter>
<Parameter>
<Name>LavoroAttivo</Name>
<Value></Value>
<ValueType>String</ValueType>
<Visible>False</Visible>
</Parameter>
<Parameter>
<Name>UltimaVista</Name>
<Value></Value>
<ValueType>String</ValueType>
<Visible>False</Visible>
</Parameter>
<Parameter>
<Name>UltimoRender</Name>
<Value></Value>
<ValueType>String</ValueType>
<Visible>False</Visible>
</Parameter>
<Parameter>
<Name>Sezione1</Name>
<Text>1 · Vista</Text>
<ValueType>Expander</ValueType>
<Parameters>
<Parameter>
<Name>VistaNome</Name>
<Text>Vista</Text>
<Value></Value>
<ValueType>String</ValueType>
<Enable>False</Enable>
</Parameter>
<Parameter>
<Name>VistaImmagine</Name>
<Value>palette_nessuna.png</Value>
<Orientation>Middle</Orientation>
<ValueType>Picture</ValueType>
<Visible>ImmaginiDaScript == 1</Visible>
</Parameter>
<Parameter>
<Name>VistaEsito</Name>
<Text>Esito</Text>
<Value></Value>
<ValueType>String</ValueType>
<Enable>False</Enable>
</Parameter>
<Parameter>
<Name>RigaCattura</Name>
<Text>Finestra attiva</Text>
<ValueType>Row</ValueType>
<Parameters>
<Parameter>
<Name>Cattura</Name>
<Text>Cattura vista</Text>
<EventId>1001</EventId>
<ValueType>Button</ValueType>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>Dimensione</Name>
<Text>Dimensione</Text>
<Value>0</Value>
<ValueType>RadioButtonGroup</ValueType>
<Parameters>
<Parameter>
<Name>Dimensione0</Name>
<Text>Come la finestra</Text>
<Value>0</Value>
<ValueType>RadioButton</ValueType>
</Parameter>
<Parameter>
<Name>Dimensione1</Name>
<Text>1920 × 1080</Text>
<Value>1</Value>
<ValueType>RadioButton</ValueType>
</Parameter>
<Parameter>
<Name>Dimensione2</Name>
<Text>3840 × 2160</Text>
<Value>2</Value>
<ValueType>RadioButton</ValueType>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>Formato</Name>
<Text>Formato</Text>
<Value>Come la finestra</Value>
<ValueList>Come la finestra|21:9 panoramico|16:9|3:2|4:3|1:1 quadrato|3:4 verticale|2:3 verticale|9:16 verticale</ValueList>
<ValueType>StringComboBox</ValueType>
</Parameter>
<Parameter>
<Name>RigaTaglio</Name>
<Text>Taglio</Text>
<ValueType>Row</ValueType>
<Parameters>
<Parameter>
<Name>VediTaglio</Name>
<Text>Vedi cosa taglia</Text>
<EventId>1008</EventId>
<ValueType>Button</ValueType>
</Parameter>
</Parameters>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>Sezione2</Name>
<Text>2 · Stile</Text>
<ValueType>Expander</ValueType>
<Parameters>
<Parameter>
<Name>Resa</Name>
<Text>Resa</Text>
<Value></Value>
<ValueType>String</ValueType>
<Enable>False</Enable>
</Parameter>
<Parameter>
<Name>Interno</Name>
<Text>Vista</Text>
<Value>0</Value>
<ValueType>RadioButtonGroup</ValueType>
<Parameters>
<Parameter>
<Name>Interno0</Name>
<Text>Esterno</Text>
<Value>0</Value>
<ValueType>RadioButton</ValueType>
</Parameter>
<Parameter>
<Name>Interno1</Name>
<Text>Interno</Text>
<Value>1</Value>
<ValueType>RadioButton</ValueType>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>PresetEsterno</Name>
<Text>Preset</Text>
<Value>Rivista d'architettura</Value>
<ValueList>Rivista d'architettura|Luce naturale calda|Pellicola morbida|Urbano editoriale|Ora blu|Notte con luna|Giornata di pioggia|Autunno nebbioso</ValueList>
<ValueType>StringComboBox</ValueType>
<Visible>Interno == 0</Visible>
</Parameter>
<Parameter>
<Name>PresetInterno</Name>
<Text>Preset</Text>
<Value>Interno rivista</Value>
<ValueList>Interno rivista|Interno caldo|Interno pellicola morbida|Interno sera|Interno notte, lampade|Interno vissuto</ValueList>
<ValueType>StringComboBox</ValueType>
<Visible>Interno == 1</Visible>
</Parameter>
<Parameter>
<Name>LuceEsterno</Name>
<Text>Ora</Text>
<Value>Come il preset</Value>
<ValueList>Come il preset|Mezzogiorno|Estate luminosa|Giorno|Ora d'oro|Ora blu|Notte con luna</ValueList>
<ValueType>StringComboBox</ValueType>
<Visible>Interno == 0</Visible>
</Parameter>
<Parameter>
<Name>LuceInterno</Name>
<Text>Luce</Text>
<Value>Come il preset</Value>
<ValueList>Come il preset|Mattino da finestra|Pomeriggio caldo|Giorno coperto|Sera, luci accese|Notte con lampade</ValueList>
<ValueType>StringComboBox</ValueType>
<Visible>Interno == 1</Visible>
</Parameter>
<Parameter>
<Name>Cielo</Name>
<Text>Cielo</Text>
<Value>Come il preset</Value>
<ValueList>Come il preset|Sereno|Coperto|Pioggia|Autunno nebbioso|Neve</ValueList>
<ValueType>StringComboBox</ValueType>
<Visible>Interno == 0</Visible>
</Parameter>
<Parameter>
<Name>Intorno</Name>
<Text>Intorno</Text>
<Value>Come il preset</Value>
<ValueList>Come il preset|Niente, sfondo neutro|Città|Periferia|Campagna</ValueList>
<ValueType>StringComboBox</ValueType>
<Visible>Interno == 0</Visible>
</Parameter>
<Parameter>
<Name>Verde</Name>
<Text>Verde, alberi</Text>
<Value>Come il preset</Value>
<ValueList>Come il preset|Nessuno|Poco|Rigoglioso</ValueList>
<ValueType>StringComboBox</ValueType>
<Visible>Interno == 0</Visible>
</Parameter>
<Parameter>
<Name>Persone</Name>
<Text>Persone</Text>
<Value>Come il preset</Value>
<ValueList>Come il preset|Nessuna|Poche|In movimento</ValueList>
<ValueType>StringComboBox</ValueType>
</Parameter>
<Parameter>
<Name>Materiali</Name>
<Text>Materiali</Text>
<Value></Value>
<ValueType>String</ValueType>
</Parameter>
<Parameter>
<Name>Modello</Name>
<Text>Modello</Text>
<Value>Nano Banana 2</Value>
<ValueList>Nano Banana 2|FLUX.1 Kontext Pro|Nano Banana Pro</ValueList>
<ValueType>StringComboBox</ValueType>
</Parameter>
<Parameter>
<Name>Risoluzione</Name>
<Text>Risoluzione del render</Text>
<Value>1K · provata</Value>
<ValueList>1K · provata|2K · da provare|4K · da provare</ValueList>
<ValueType>StringComboBox</ValueType>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>Sezione3</Name>
<Text>3 · Invio</Text>
<ValueType>Expander</ValueType>
<Parameters>
<Parameter>
<Name>Destinazione</Name>
<Text>La vista va a</Text>
<Value></Value>
<ValueType>String</ValueType>
<Enable>False</Enable>
</Parameter>
<Parameter>
<Name>NotaInvio</Name>
<Text>Ripiego</Text>
<Value></Value>
<ValueType>String</ValueType>
<Enable>False</Enable>
</Parameter>
<Parameter>
<Name>Costo</Name>
<Text>Costo</Text>
<Value></Value>
<ValueType>String</ValueType>
<Enable>False</Enable>
</Parameter>
<Parameter>
<Name>Stato</Name>
<Text>Stato</Text>
<Value></Value>
<ValueType>String</ValueType>
<Enable>False</Enable>
</Parameter>
<Parameter>
<Name>RigaInvio</Name>
<Text>Motore</Text>
<ValueType>Row</ValueType>
<Parameters>
<Parameter>
<Name>Genera</Name>
<Text>Genera render</Text>
<EventId>1003</EventId>
<ValueType>Button</ValueType>
<Visible>InCorso == 0</Visible>
</Parameter>
<Parameter>
<Name>Annulla</Name>
<Text>Annulla</Text>
<EventId>1004</EventId>
<ValueType>Button</ValueType>
<Visible>InCorso == 1</Visible>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>RigaAggiorna</Name>
<Text>Stato del lavoro</Text>
<ValueType>Row</ValueType>
<Parameters>
<Parameter>
<Name>Aggiorna</Name>
<Text>Aggiorna</Text>
<EventId>1005</EventId>
<ValueType>Button</ValueType>
</Parameter>
</Parameters>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>Sezione4</Name>
<Text>4 · Ultimo render</Text>
<ValueType>Expander</ValueType>
<Parameters>
<Parameter>
<Name>Ultimo</Name>
<Text>Ultimo</Text>
<Value></Value>
<ValueType>String</ValueType>
<Enable>False</Enable>
</Parameter>
<Parameter>
<Name>UltimoImmagine</Name>
<Value>palette_nessuna.png</Value>
<Orientation>Middle</Orientation>
<ValueType>Picture</ValueType>
<Visible>ImmaginiDaScript == 1</Visible>
</Parameter>
<Parameter>
<Name>RigaStudio</Name>
<Text>Studio</Text>
<ValueType>Row</ValueType>
<Parameters>
<Parameter>
<Name>ApriStudio</Name>
<Text>Apri nello Studio</Text>
<EventId>1006</EventId>
<ValueType>Button</ValueType>
</Parameter>
<Parameter>
<Name>ApriCartella</Name>
<Text>Apri cartella</Text>
<EventId>1007</EventId>
<ValueType>Button</ValueType>
</Parameter>
</Parameters>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>Sezione5</Name>
<Text>In arrivo</Text>
<ValueType>Expander</ValueType>
<Parameters>
<Parameter>
<Name>InArrivo0</Name>
<Text>Cambia materiale: in arrivo, non ancora attivo</Text>
<ValueType>Text</ValueType>
</Parameter>
<Parameter>
<Name>InArrivo1</Name>
<Text>Annota aree: in arrivo, non ancora attivo</Text>
<ValueType>Text</ValueType>
</Parameter>
<Parameter>
<Name>InArrivo2</Name>
<Text>Livelli: in arrivo, non ancora attivo</Text>
<ValueType>Text</ValueType>
</Parameter>
<Parameter>
<Name>InArrivo3</Name>
<Text>Video: in arrivo, non ancora attivo</Text>
<ValueType>Text</ValueType>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>Cartella</Name>
<Text>Cartella delle viste (vuota = Usr\AIRENDER\viste)</Text>
<Value></Value>
<ValueType>String</ValueType>
</Parameter>
</Parameters>
</Page>
</Element>
