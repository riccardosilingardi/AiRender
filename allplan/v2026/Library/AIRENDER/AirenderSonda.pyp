<?xml version='1.0' encoding='UTF-8'?>
<Element xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd">
    <Script>
        <Name>airender\AirenderSonda.py</Name>
        <Title>AIRENDER sonda</Title>
        <Version>0.1</Version>
    </Script>
    <Page>
        <Name>Pagina</Name>
        <Text>AIRENDER sonda</Text>
        <Parameters>
            <Parameter>
                <Name>Spiegazione</Name>
                <Text>Premi i pulsanti dall'alto in basso. Ogni risposta finisce in Usr\...\AIRENDER\sonda\risultati-sonda.txt</Text>
                <ValueType>Text</ValueType>
            </Parameter>

            <Parameter>
                <Name>Domanda1</Name>
                <Text>1 · Un'immagine si cambia da script?</Text>
                <ValueType>Expander</ValueType>
                <Parameters>
                    <Parameter>
                        <Name>TestoFissa</Name>
                        <Text>Prima: stesso file, riscritto</Text>
                        <ValueType>Text</ValueType>
                    </Parameter>
                    <Parameter>
                        <Name>AnteprimaFissa</Name>
                        <Value>sonda_anteprima.png</Value>
                        <Orientation>Middle</Orientation>
                        <ValueType>Picture</ValueType>
                    </Parameter>
                    <Parameter>
                        <Name>TestoVariabile</Name>
                        <Text>Seconda: percorso cambiato</Text>
                        <ValueType>Text</ValueType>
                    </Parameter>
                    <Parameter>
                        <Name>AnteprimaVariabile</Name>
                        <Value>sonda_a.png</Value>
                        <Orientation>Middle</Orientation>
                        <ValueType>Picture</ValueType>
                    </Parameter>
                    <Parameter>
                        <Name>RigaImmagine</Name>
                        <Text>Immagini</Text>
                        <ValueType>Row</ValueType>
                        <Parameters>
                            <Parameter>
                                <Name>CambiaImmagine</Name>
                                <Text>Cambia immagine</Text>
                                <EventId>2001</EventId>
                                <ValueType>Button</ValueType>
                            </Parameter>
                        </Parameters>
                    </Parameter>
                </Parameters>
            </Parameter>

            <Parameter>
                <Name>Domanda2</Name>
                <Text>2 · Miniature da file</Text>
                <ValueType>Expander</ValueType>
                <Parameters>
                    <Parameter>
                        <Name>Miniature</Name>
                        <Text>Fotorealistico|Plastico bianco|Schizzo|Acquerello|Cinematografico</Text>
                        <Value>1</Value>
                        <ValueList>1|2|3|4|5</ValueList>
                        <ValueList2>sonda_foto.png|sonda_plastico.png|sonda_schizzo.png|sonda_acquerello.png|sonda_cinema.png</ValueList2>
                        <ValueType>PictureButtonList</ValueType>
                    </Parameter>
                    <Parameter>
                        <Name>RigaMiniatura</Name>
                        <Text>Scelta</Text>
                        <ValueType>Row</ValueType>
                        <Parameters>
                            <Parameter>
                                <Name>RegistraMiniatura</Name>
                                <Text>Registra la scelta</Text>
                                <EventId>2002</EventId>
                                <ValueType>Button</ValueType>
                            </Parameter>
                        </Parameters>
                    </Parameter>
                </Parameters>
            </Parameter>

            <Parameter>
                <Name>Domanda3</Name>
                <Text>3-5 · Processo a parte, Edge, Allplan libero</Text>
                <ValueType>Expander</ValueType>
                <Parameters>
                    <Parameter>
                        <Name>RigaPython</Name>
                        <Text>3 · Quale Python</Text>
                        <ValueType>Row</ValueType>
                        <Parameters>
                            <Parameter>
                                <Name>TrovaPython</Name>
                                <Text>Trova Python</Text>
                                <EventId>2003</EventId>
                                <ValueType>Button</ValueType>
                            </Parameter>
                        </Parameters>
                    </Parameter>
                    <Parameter>
                        <Name>RigaAvvia</Name>
                        <Text>3 · Processo</Text>
                        <ValueType>Row</ValueType>
                        <Parameters>
                            <Parameter>
                                <Name>Avvia</Name>
                                <Text>Avvia processo</Text>
                                <EventId>2004</EventId>
                                <ValueType>Button</ValueType>
                            </Parameter>
                        </Parameters>
                    </Parameter>
                    <Parameter>
                        <Name>RigaControlla</Name>
                        <Text>5 · Allplan libero?</Text>
                        <ValueType>Row</ValueType>
                        <Parameters>
                            <Parameter>
                                <Name>Controlla</Name>
                                <Text>Controlla processo</Text>
                                <EventId>2005</EventId>
                                <ValueType>Button</ValueType>
                            </Parameter>
                        </Parameters>
                    </Parameter>
                    <Parameter>
                        <Name>RigaEdge</Name>
                        <Text>4 · Finestra Edge</Text>
                        <ValueType>Row</ValueType>
                        <Parameters>
                            <Parameter>
                                <Name>ApriEdge</Name>
                                <Text>Apri in Edge</Text>
                                <EventId>2006</EventId>
                                <ValueType>Button</ValueType>
                            </Parameter>
                        </Parameters>
                    </Parameter>
                </Parameters>
            </Parameter>

            <Parameter>
                <Name>RigaRiepilogo</Name>
                <Text>Alla fine</Text>
                <ValueType>Row</ValueType>
                <Parameters>
                    <Parameter>
                        <Name>Riepilogo</Name>
                        <Text>Riepilogo</Text>
                        <EventId>2007</EventId>
                        <ValueType>Button</ValueType>
                    </Parameter>
                </Parameters>
            </Parameter>
        </Parameters>
    </Page>
</Element>
